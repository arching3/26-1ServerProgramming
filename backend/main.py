"""
FastAPI 시작점입니다.

실행 예시:
uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import MenuRequest, get_service_info, recommend_menu_api

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


@app.get("/info")
def get_info() -> dict:
    """Return service and frontend integration information."""
    return get_service_info()


@app.post("/api/recommend-menu")
def recommend_menu(data: MenuRequest) -> dict:
    """Recommend menus and nearby restaurants."""
    return recommend_menu_api(data)
