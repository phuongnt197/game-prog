from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from .. import db


SESSION_COOKIE = "aip1_session"


def optional_user(aip1_session: Annotated[str | None, Cookie()] = None) -> dict | None:
    return db.user_for_session(aip1_session)


def current_user(user: Annotated[dict | None, Depends(optional_user)]) -> dict:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")
    return user


def admin_user(user: Annotated[dict, Depends(current_user)]) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


CurrentUser = Annotated[dict, Depends(current_user)]
AdminUser = Annotated[dict, Depends(admin_user)]
