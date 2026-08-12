from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ... import db
from ..dependencies import AdminUser
from ..schemas import CreateUserRequest, Payload, ResetPasswordRequest, UnlockRequest


router = APIRouter(prefix="/api/admin", tags=["administration"])


@router.get("/overview")
def overview(user: AdminUser) -> dict:
    return db.admin_overview()


@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, user: AdminUser) -> dict:
    created = db.create_user(username=body.username, password=body.password, display_name=body.display_name or body.username, role=body.role, must_change_password=True)
    return {"user": db.public_user(created)}


@router.post("/unlock")
def unlock(body: UnlockRequest, user: AdminUser) -> dict:
    db.unlock_assignment(body.user_id, body.assignment_id, user["id"])
    return {"ok": True}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, user: AdminUser) -> dict:
    db.reset_password(body.user_id, body.password)
    return {"ok": True}


@router.get("/bug-problems")
def bug_problems(user: AdminUser) -> dict:
    return {"problems": db.list_bug_problems(include_inactive=True, activity_type=None)}


@router.get("/bug-problems/{problem_id}")
def bug_problem(problem_id: str, user: AdminUser) -> dict:
    problem = db.get_bug_problem(problem_id, include_secret=True)
    if not problem:
        raise HTTPException(404, "Bug-detection problem not found")
    return problem


@router.post("/bug-problems", status_code=201)
def save_bug_problem(body: Payload, user: AdminUser) -> dict:
    return {"problem": db.save_bug_problem(body.model_dump())}


@router.get("/learning-problems")
def learning_problems(user: AdminUser) -> dict:
    return {"problems": db.list_bug_problems(include_inactive=True, activity_type=None)}


@router.get("/learning-problems/{problem_id}")
def learning_problem(problem_id: str, user: AdminUser) -> dict:
    problem = db.get_bug_problem(problem_id, include_secret=True)
    if not problem:
        raise HTTPException(404, "Learning problem not found")
    return problem


@router.post("/learning-problems", status_code=201)
def save_learning_problem(body: Payload, user: AdminUser) -> dict:
    return {"problem": db.save_bug_problem(body.model_dump())}
