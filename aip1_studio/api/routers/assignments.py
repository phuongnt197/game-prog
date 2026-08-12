from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ... import db
from ...assignments import ASSIGNMENTS, get_assignment, public_assignment
from ...services.execution import run_assignment
from ..dependencies import CurrentUser
from ..schemas import AssignmentRunRequest, DraftRequest


router = APIRouter(prefix="/api/assignments", tags=["learning fundamentals"])


@router.get("")
def list_assignments(user: CurrentUser) -> dict:
    completed = db.completed_assignment_ids(user["id"])
    drafts = db.assignment_drafts(user["id"])
    items = []
    for assignment in ASSIGNMENTS:
        unlocked = db.is_assignment_unlocked(user, assignment["id"])
        item = public_assignment(assignment, unlocked, assignment["id"] in completed)
        if unlocked and assignment["id"] in drafts:
            item.update({"draft_code": drafts[assignment["id"]]["code"], "draft_updated_at": drafts[assignment["id"]]["updated_at"]})
        items.append(item)
    return {"assignments": items}


@router.get("/{assignment_id}")
def assignment_detail(assignment_id: str, user: CurrentUser) -> dict:
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    unlocked = db.is_assignment_unlocked(user, assignment_id)
    if not unlocked:
        raise HTTPException(403, "Assignment is locked")
    item = public_assignment(assignment, True, assignment_id in db.completed_assignment_ids(user["id"]))
    draft = db.assignment_draft(user["id"], assignment_id)
    if draft:
        item.update({"draft_code": draft["code"], "draft_updated_at": draft["updated_at"]})
    return item


@router.post("/{assignment_id}/draft")
def save_draft(assignment_id: str, body: DraftRequest, user: CurrentUser) -> dict:
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    if not db.is_assignment_unlocked(user, assignment_id):
        raise HTTPException(403, "Assignment is locked")
    draft = db.save_assignment_draft(user["id"], assignment_id, body.code)
    return {"ok": True, "assignment_id": assignment_id, "updated_at": draft["updated_at"]}


@router.post("/{assignment_id}/run")
def run(assignment_id: str, body: AssignmentRunRequest, user: CurrentUser) -> dict:
    db.save_assignment_draft(user["id"], assignment_id, body.code)
    return run_assignment(user, assignment_id, body.code, case_index=body.case_index)


@router.post("/{assignment_id}/submit")
def submit(assignment_id: str, body: DraftRequest, user: CurrentUser) -> dict:
    result = run_assignment(user, assignment_id, body.code, run_all=True)
    db.record_submission(user["id"], assignment_id, body.code, result)
    result["completed"] = bool(result.get("passed"))
    return result
