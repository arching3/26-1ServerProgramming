"""
FastAPI 시작점입니다.

실행 예시:
uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Menu Recommendation API")


class RecommendMenuRequest(BaseModel):
    date: str
    time: str
    place: str
    people_count: int
    preferences: str
    avoid_foods: str
    budget: str


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/recommend-menu")
def recommend_menu(request: RecommendMenuRequest) -> dict[str, object]:
    return {
        "message": "메뉴 추천 요청을 받았습니다.",
        "data": request.model_dump(),
    }
