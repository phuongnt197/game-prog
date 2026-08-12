from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response

from ... import db
from ..dependencies import SESSION_COOKIE, CurrentUser, optional_user
from ..schemas import BehaviorRequest, ChangePasswordRequest, LoginRequest, RegisterRequest


router = APIRouter(prefix="/api", tags=["authentication"])


def _set_session(response: Response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, max_age=db.SESSION_SECONDS, httponly=True, samesite="lax", path="/")


@router.get("/me")
def me(user: dict | None = Depends(optional_user)) -> dict:
    return {"user": db.public_user(user) if user else None}


@router.post("/auth/login")
def login(body: LoginRequest, response: Response) -> dict:
    user = db.authenticate(body.username, body.password)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(401, "Invalid username or password")
    _set_session(response, db.create_session(user["id"]))
    return {"user": db.public_user(user)}


@router.post("/auth/register")
def register(body: RegisterRequest, response: Response) -> dict:
    user = db.create_user(username=body.username, password=body.password, display_name=body.display_name or body.username, role="student", must_change_password=False)
    _set_session(response, db.create_session(user["id"]))
    return {"user": db.public_user(user)}


@router.post("/auth/logout")
def logout(response: Response, aip1_session: str | None = Cookie(default=None)) -> dict:
    if aip1_session:
        db.delete_session(aip1_session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.post("/auth/change-password")
def change_password(body: ChangePasswordRequest, user: CurrentUser) -> dict:
    db.change_password(user["id"], body.old_password, body.new_password)
    return {"user": db.public_user(db.get_user_by_id(user["id"]))}


@router.post("/behavior/log")
def behavior(body: BehaviorRequest, user: CurrentUser) -> dict:
    db.log_events(user["id"], body.events)
    return {"ok": True}
