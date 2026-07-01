from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .config import PROJECTS_DIR


def list_projects() -> list[dict[str, Any]]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    projects = []
    for path in PROJECTS_DIR.glob("*.json"):
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        projects.append(_public_project(project, include_code=False))
    return sorted(projects, key=lambda item: item.get("updated_at", ""), reverse=True)


def get_project(slug: str) -> dict[str, Any] | None:
    path = _project_path(slug)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_project(payload: dict[str, Any]) -> dict[str, Any]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    now = _iso_now()
    title = str(payload.get("title") or "Untitled Project").strip()[:120]
    creator = str(payload.get("creator") or "Anonymous").strip()[:80]
    slug = _unique_slug(payload.get("slug") or title)
    existing = get_project(slug) if slug else None
    project = {
        "slug": slug,
        "title": title,
        "creator": creator,
        "description": str(payload.get("description") or "").strip()[:800],
        "template_id": str(payload.get("template_id") or "adventure"),
        "code": str(payload.get("code") or ""),
        "tests": str(payload.get("tests") or "[]"),
        "specification": str(payload.get("specification") or ""),
        "ai_record": str(payload.get("ai_record") or ""),
        "created_at": (existing or {}).get("created_at") or now,
        "updated_at": now,
    }
    _project_path(slug).write_text(json.dumps(project, indent=2), encoding="utf-8")
    return project


def _project_path(slug: str) -> Path:
    return PROJECTS_DIR / f"{_slugify(slug)}.json"


def _slugify(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or "project"


def _unique_slug(value: Any) -> str:
    base = _slugify(value)
    slug = base
    index = 2
    while _project_path(slug).exists():
        slug = f"{base}-{index}"
        index += 1
    return slug


def _public_project(project: dict[str, Any], include_code: bool) -> dict[str, Any]:
    public = {
        "slug": project.get("slug"),
        "title": project.get("title"),
        "creator": project.get("creator"),
        "description": project.get("description"),
        "template_id": project.get("template_id"),
        "created_at": project.get("created_at"),
        "updated_at": project.get("updated_at"),
    }
    if include_code:
        public.update(
            {
                "code": project.get("code", ""),
                "tests": project.get("tests", "[]"),
                "specification": project.get("specification", ""),
                "ai_record": project.get("ai_record", ""),
            }
        )
    return public


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
