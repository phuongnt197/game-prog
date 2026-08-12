from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import db
from ..config import FRONTEND_DIR, JUDGE0_HOST, JUDGE0_PORT, OPENAI_BASE_URL, OPENAI_MODEL, SERVER_HOST, SERVER_PORT
from .routers import admin, ai_education, assignments, auth, bug_lab, human_code, showcase


FRONTEND_DIST = FRONTEND_DIR / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


def create_app(*, serve_frontend: bool = True) -> FastAPI:
    app = FastAPI(title="AIP1 Studio API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @app.exception_handler(PermissionError)
    async def permission_error_handler(_: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=403)

    @app.get("/api/health", tags=["system"])
    def health() -> dict:
        return {
            "ok": True, "judge0": f"{JUDGE0_HOST}:{JUDGE0_PORT}",
            "openai_base_url": OPENAI_BASE_URL, "openai_model": OPENAI_MODEL,
        }

    app.include_router(auth.router)
    app.include_router(assignments.router)
    app.include_router(bug_lab.router)
    app.include_router(human_code.router)
    app.include_router(ai_education.router)
    app.include_router(showcase.router)
    app.include_router(admin.router)

    if serve_frontend and FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    elif serve_frontend:
        @app.get("/", include_in_schema=False)
        def frontend_missing() -> dict:
            return {"message": "Frontend build not found. Run `npm run build` in pacman-python-website."}
    return app


app = create_app()


def main() -> None:
    uvicorn.run("aip1_studio.api.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
