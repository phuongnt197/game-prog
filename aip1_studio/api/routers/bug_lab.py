from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ... import db
from ...services.bug_generation import stream_bug_generation
from ...services.execution import run_bug_lab
from ..dependencies import CurrentUser
from ..schemas import BugFixRequest, BugTestsRequest


router = APIRouter(prefix="/api/bug-problems", tags=["detecting AI bugs"])


@router.get("")
def list_problems(user: CurrentUser) -> dict:
    return {"problems": db.list_bug_problems(user["id"])}


@router.get("/{problem_id}")
def problem_detail(problem_id: str, user: CurrentUser) -> dict:
    problem = db.get_public_bug_problem(problem_id, user["id"])
    if not problem or not problem["active"]:
        raise HTTPException(404, "Bug-detection problem not found")
    return problem


@router.post("/{problem_id}/generate")
def generate_solution(problem_id: str, user: CurrentUser) -> StreamingResponse:
    problem = db.get_activity_problem(problem_id, "bug", include_secret=True)
    if not problem or not problem["active"]:
        raise HTTPException(404, "Bug-detection problem not found")
    return StreamingResponse(
        stream_bug_generation(user, problem),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{problem_id}/validate-tests")
def validate_tests(problem_id: str, body: BugTestsRequest, user: CurrentUser) -> dict:
    return run_bug_lab(user, problem_id, body.model_dump(), "tests")


@router.post("/{problem_id}/submit-fix")
def submit_fix(problem_id: str, body: BugFixRequest, user: CurrentUser) -> dict:
    return run_bug_lab(user, problem_id, body.model_dump(), "fix")
