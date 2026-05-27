"""API-facing business flow for menu recommendation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, root_validator

from backend.ai import make_restaurant_reason, recommend_menus_with_weather
from backend.place import search_restaurants
from backend.weather import get_weather


class MenuRequest(BaseModel):
    """Request body for POST /api/recommend-menu.

    FastAPI receives JSON from the frontend and converts it into this Pydantic
    object. Because `data` is an object, values are accessed with dot notation
    such as `data.date`, `data.time`, and `data.place`.
    """

    date: str
    time: str
    place: str
    people_count: int
    preferences: str
    avoid_foods: str
    budget: str

    class Config:
        populate_by_name = True
        extra = "ignore"

    @root_validator(pre=True)
    def accept_pdf_preference_field(cls, values: dict) -> dict:
        """Accept PDF's `preference` field while recommending `preferences`."""
        if "preferences" not in values and "preference" in values:
            values["preferences"] = values["preference"]
        return values


def get_service_info() -> dict:
    """Return backend service information and frontend integration contract."""
    return {
        "service_name": "오늘 뭐 먹지?",
        "description": (
            "날씨와 사용자 조건을 바탕으로 메뉴 3개를 추천하고, "
            "Kakao Local API로 주변 음식점을 검색하는 FastAPI 백엔드입니다."
        ),
        "apis": [
            {
                "method": "GET",
                "path": "/info",
                "description": "서비스 정보와 프론트엔드 연동 명세를 반환합니다.",
            },
            {
                "method": "POST",
                "path": "/api/recommend-menu",
                "description": "날씨, 메뉴 추천, 음식점 검색 결과를 반환합니다.",
            },
        ],
        "frontend_contract": {
            "request_url": "POST http://127.0.0.1:8000/api/recommend-menu",
            "content_type": "application/json",
            "required_fields": {
                "date": "str - 모임 날짜, 예: 2026-05-24",
                "time": "str - 모임 시간, 예: 18:00",
                "place": "str - 모임 장소, 예: 강남역",
                "people_count": "int - 인원수, 예: 4",
                "preferences": "str - 선호 음식 종류, 예: 한식",
                "avoid_foods": "str - 피해야 하는 음식/식재료, 예: 회, 해산물",
                "budget": "str - 총 예산 또는 예산 설명, 예: 30000",
            },
            "compatibility_note": (
                "PDF 명세의 preference 단수 필드는 호환 입력으로만 지원할 수 있습니다. "
                "프론트엔드는 preferences 복수 필드명을 사용하는 것을 권장합니다."
            ),
            "example_request": {
                "date": "2026-05-24",
                "time": "18:00",
                "place": "강남역",
                "people_count": 4,
                "preferences": "한식",
                "avoid_foods": "회, 해산물",
                "budget": "30000",
            },
            "response_shape": {
                "weather": "dict",
                "menus": "list[dict]",
                "restaurants": "list[dict]",
            },
        },
        "environment_variables": {
            "KMA_API_KEY": "기상청 API 키. 없으면 mock 날씨를 사용합니다.",
            "KAKAO_REST_API_KEY": "Kakao REST API 키. 없으면 mock 음식점을 사용합니다.",
            "LLM_API_KEY": "향후 실제 LLM API 연동 시 사용할 키입니다. 현재는 mock LLM을 사용합니다.",
            "LLM_MODEL": "향후 실제 LLM API 연동 시 사용할 모델명입니다. 현재는 mock LLM을 사용합니다.",
        },
    }


def _request_to_input_dict(data: MenuRequest) -> dict[str, Any]:
    return {
        "date": data.date,
        "time": data.time,
        "place": data.place,
        "people_count": data.people_count,
        "preferences": data.preferences,
        "avoid_foods": data.avoid_foods,
        "budget": data.budget,
    }


def recommend_menu_api(data: MenuRequest) -> dict:
    """Run the full recommendation flow and return internal response data."""
    weather = get_weather(data.date, data.time, data.place)

    menu_result = recommend_menus_with_weather(
        date=data.date,
        time=data.time,
        place=data.place,
        people_count=data.people_count,
        preferences=data.preferences,
        avoid_foods=data.avoid_foods,
        budget=data.budget,
        weather=weather,
    )
    menus = menu_result["menus"]

    restaurants = search_restaurants(data.place, menus)
    for restaurant in restaurants:
        restaurant["selection_reason"] = make_restaurant_reason(
            restaurant=restaurant,
            matched_menu=restaurant.get("matched_menu", ""),
            people_count=data.people_count,
            budget=data.budget,
            preferences=data.preferences,
            avoid_foods=data.avoid_foods,
            place=data.place,
            time=data.time,
            weather=weather,
        )

    return {
        "input": _request_to_input_dict(data),
        "weather": weather,
        "menus": menus,
        "restaurants": restaurants,
    }
