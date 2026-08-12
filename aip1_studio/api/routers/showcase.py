from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ... import db
from ..dependencies import CurrentUser


router = APIRouter(prefix="/api/projects", tags=["showcase"])


@router.get("")
def projects(user: CurrentUser) -> dict:
    return {"projects": db.list_projects()}


@router.get("/{slug}")
def project(slug: str, user: CurrentUser) -> dict:
    item = db.get_project(slug)
    if not item:
        raise HTTPException(404, "Project not found")
    return item
