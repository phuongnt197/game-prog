from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ... import db
from ...services.human_code import run_visible_tests, stream_copilot, submit_solution
from ..dependencies import CurrentUser
from ..schemas import HumanChatRequest, HumanWorkRequest


router = APIRouter(prefix="/api/human-code", tags=["human code, AI tests"])


@router.get("")
def problems(user: CurrentUser) -> dict:
    return {"problems": db.list_human_code_problems(user["id"])}


@router.post("/{problem_id}/draft")
def save_draft(problem_id: str, body: HumanWorkRequest, user: CurrentUser) -> dict:
    problem = db.get_activity_problem(problem_id, "human", include_secret=True)
    if not problem or not problem["active"]:
        raise HTTPException(404, "Programming problem not found")
    db.save_human_code_draft(user["id"], problem_id, body.solution_code, body.test_code)
    return {"ok": True}


@router.post("/{problem_id}/run-tests")
def run_tests(problem_id: str, body: HumanWorkRequest, user: CurrentUser) -> dict:
    return run_visible_tests(user, problem_id, body.model_dump())


@router.post("/{problem_id}/submit")
def submit(problem_id: str, body: HumanWorkRequest, user: CurrentUser) -> dict:
    return submit_solution(user, problem_id, body.model_dump())


@router.post("/{problem_id}/chat")
def chat(problem_id: str, body: HumanChatRequest, user: CurrentUser) -> StreamingResponse:
    problem = db.get_activity_problem(problem_id, "human", include_secret=True)
    if not problem or not problem["active"]:
        raise HTTPException(404, "Programming problem not found")
    return StreamingResponse(
        stream_copilot(problem, body.message, body.solution_code, body.test_code, body.history),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
