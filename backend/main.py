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
    people_count: str
    preference: str
    avoid_foods: str
    budget: str


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/recommend-menu")
def recommend_menu(request: RecommendMenuRequest) -> dict[str, object]:
    request_data = request.model_dump()

    return {
        "weather": {
            "date": request_data["date"],
            "time": request_data["time"],
            "place": request_data["place"],
            "condition": "맑음",
            "temperature": 23,
            "rain_probability": 20,
            "summary": "맑고 따뜻한 날씨입니다.",
            "source": "EXAMPLE_DATA",
            "is_mock": True,
        },
        "menus": [
            {
                "rank": 1,
                "name": "소불고기 정식",
                "category": request_data["preference"],
                "price_estimate": "22000원",
                "reason": "선호 음식 종류와 예산을 고려했을 때 함께 먹기 좋은 메뉴입니다.",
                "weather_reason": "맑은 날씨에 부담 없이 먹기 좋은 따뜻한 한식 메뉴입니다.",
                "recommend_score": 95,
            },
            {
                "rank": 2,
                "name": "김치찌개",
                "category": request_data["preference"],
                "price_estimate": "18000원",
                "reason": "예산 안에서 여러 명이 나누어 먹기 좋고 피해야 할 음식과 충돌하지 않습니다.",
                "weather_reason": "따뜻한 국물 메뉴라 식사 만족도가 높을 수 있습니다.",
                "recommend_score": 91,
            },
        ],
        "restaurants": [
            {
                "name": "강남 한식당",
                "category": "한식",
                "address": "서울 강남구 역삼동 000-0",
                "road_address": "서울 강남구 테헤란로 000",
                "phone": "02-0000-0000",
                "place_url": "https://place.example.com/restaurant-1",
                "x": "127.0276",
                "y": "37.4979",
                "matched_menu": "소불고기 정식",
            },
            {
                "name": "역삼 김치찌개",
                "category": "한식",
                "address": "서울 강남구 역삼동 111-1",
                "road_address": "서울 강남구 강남대로 111",
                "phone": "02-1111-1111",
                "place_url": "https://place.example.com/restaurant-2",
                "x": "127.0280",
                "y": "37.4982",
                "matched_menu": "김치찌개",
            },
        ],
    }
