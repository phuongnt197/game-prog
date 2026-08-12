from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from ...services.ai_education import education_video_path, manim_available, stream_education_video
from ..dependencies import CurrentUser
from ..schemas import EducationVideoRequest


router = APIRouter(prefix="/api/ai-education", tags=["AI education"])


@router.get("/capabilities")
def capabilities(user: CurrentUser) -> dict:
    available = manim_available()
    return {
        "ok": True,
        "renderer_available": available,
        "message": "Manim is ready." if available else "Manim is not installed on the FastAPI server.",
    }


@router.post("/generate")
def generate_video(body: EducationVideoRequest, user: CurrentUser) -> StreamingResponse:
    return StreamingResponse(
        stream_education_video(user, body.question),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/videos/{video_id}")
def video(video_id: str, user: CurrentUser) -> FileResponse:
    path = education_video_path(user["id"], video_id)
    if not path:
        raise HTTPException(404, "Lesson video not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        headers={"Cache-Control": "private, max-age=3600"},
    )
