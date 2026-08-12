from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "pacman-python-website"
DATA_DIR = ROOT_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"
AI_EDUCATION_DIR = DATA_DIR / "ai_education"

JUDGE0_HOST = os.getenv("JUDGE0_HOST", "http://<URL>").rstrip("/")
JUDGE0_PORT = int(os.getenv("JUDGE0_PORT", "2358"))
JUDGE0_LANGUAGE_ID = int(os.getenv("JUDGE0_LANGUAGE_ID", "33"))
JUDGE0_POLL_INTERVAL = float(os.getenv("JUDGE0_POLL_INTERVAL", "0.5"))
JUDGE0_TIME_LIMIT = float(os.getenv("JUDGE0_TIME_LIMIT", "8"))
JUDGE0_MEMORY_LIMIT = int(os.getenv("JUDGE0_MEMORY_LIMIT", "256000"))

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://<URL>").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "Qwen/Qwen3.6-35B-A3B")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "EMPTY")

MANIM_RENDER_TIMEOUT = int(os.getenv("MANIM_RENDER_TIMEOUT", "120"))

SERVER_HOST = os.getenv("AIP1_HOST", "localhost")
SERVER_PORT = int(os.getenv("AIP1_PORT", "8002"))
