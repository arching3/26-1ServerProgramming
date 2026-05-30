"""API boundary for menu recommendation."""

from __future__ import annotations

import logging

from pydantic import BaseModel, root_validator

from backend.recommendation_flow import recommend_menu_flow

logger = logging.getLogger("backend.api")


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
    logger.info("get_service_info.start")
    info = {
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
                "restaurants": "list[dict] - LLM 추천과 연결된 실제 Kakao Map 상호명 후보",
            },
        },
        "environment_variables": {
            "KMA_SHORT_API_KEY_ENCODE": "기상청 단기예보 API 인코딩 키입니다.",
            "KAKAO_REST_API_KEY": "Kakao REST API 키. 없으면 mock 음식점을 사용합니다.",
            "GOOGLE_MAPS_API_KEY": "Google Places API 키. 있으면 음식점 Google 평점을 보강합니다.",
            "GOOGLE_API_KEY": "Gemini LLM 호출에 사용할 Google API 키입니다.",
            "GEMINI_API_KEY": "GOOGLE_API_KEY 대신 사용할 수 있는 Gemini API 키입니다.",
            "OPENAI_API_KEY": "Gemini 실패 시 OpenAI fallback 호출에 사용할 키입니다.",
        },
    }
    logger.info("get_service_info.done apis=%s", len(info["apis"]))
    return info


def recommend_menu_api(data: MenuRequest) -> dict:
    """Run the full recommendation flow and return internal response data."""
    return recommend_menu_flow(data)
