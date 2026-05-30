"""
FastAPI 시작점입니다.

실행 예시:
uvicorn backend.main:app --reload
"""

import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api import MenuRequest, get_service_info, recommend_menu_api


def configure_logging() -> logging.Logger:
    """Configure stdout logging and a shared project error log file."""
    project_root = Path(__file__).resolve().parents[1]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(getattr(handler, "_project_stdout", False) for handler in root_logger.handlers):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(formatter)
        stdout_handler._project_stdout = True
        root_logger.addHandler(stdout_handler)

    if not any(getattr(handler, "_project_error_file", False) for handler in root_logger.handlers):
        error_handler = logging.FileHandler(logs_dir / "error.log", encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler._project_error_file = True
        root_logger.addHandler(error_handler)

    return logging.getLogger("backend")


logger = configure_logging()

app = FastAPI(title="오늘 뭐 먹지? Backend")

# Development CORS setting. This allows a separate frontend team to call this
# backend from any local development origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log backend requests and capture unhandled errors."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled backend error method=%s path=%s elapsed_seconds=%.3f",
            request.method,
            request.url.path,
            time.perf_counter() - start,
        )
        raise

    if response.status_code >= 500:
        logger.error(
            "Backend response error method=%s path=%s status=%s elapsed_seconds=%.3f",
            request.method,
            request.url.path,
            response.status_code,
            time.perf_counter() - start,
        )
    else:
        logger.info(
            "Backend request method=%s path=%s status=%s elapsed_seconds=%.3f",
            request.method,
            request.url.path,
            response.status_code,
            time.perf_counter() - start,
        )
    return response


@app.get("/info")
def get_info() -> dict:
    """Return service and frontend integration information."""
    return get_service_info()


@app.post("/api/recommend-menu")
def recommend_menu(data: MenuRequest) -> dict:
    """Recommend menus and nearby restaurants."""
    return recommend_menu_api(data)
