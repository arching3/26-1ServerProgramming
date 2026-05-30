"""API-facing business flow for menu recommendation."""

from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import BaseModel, root_validator

from backend.ai import make_restaurant_reason, recommend_menus_with_weather
from backend.google_places import enrich_restaurants_with_google_ratings
from backend.place import match_restaurants_to_menus, search_nearby_restaurants
from backend.weather import get_weather

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
            "KMA_API_KEY": "기상청 API 키. 없으면 mock 날씨를 사용합니다.",
            "KAKAO_REST_API_KEY": "Kakao REST API 키. 없으면 mock 음식점을 사용합니다.",
            "GOOGLE_MAPS_API_KEY": "Google Places API 키. 있으면 음식점 Google 평점을 보강합니다.",
            "LLM_API_KEY": "향후 실제 LLM API 연동 시 사용할 키입니다. 현재는 mock LLM을 사용합니다.",
            "LLM_MODEL": "향후 실제 LLM API 연동 시 사용할 모델명입니다. 현재는 mock LLM을 사용합니다.",
        },
    }
    logger.info("get_service_info.done apis=%s", len(info["apis"]))
    return info


def _request_to_input_dict(data: MenuRequest) -> dict[str, Any]:
    logger.info("_request_to_input_dict.start place=%s", data.place)
    result = {
        "date": data.date,
        "time": data.time,
        "place": data.place,
        "people_count": data.people_count,
        "preferences": data.preferences,
        "avoid_foods": data.avoid_foods,
        "budget": data.budget,
    }
    logger.info("_request_to_input_dict.done keys=%s", len(result))
    return result


def recommend_menu_api(data: MenuRequest) -> dict:
    """Run the full recommendation flow and return internal response data."""
    logger.info(
        "recommend_api.start place=%s people=%s preferences=%s budget=%s",
        data.place,
        data.people_count,
        data.preferences,
        data.budget,
    )
    start = time.perf_counter()

    weather_start = time.perf_counter()
    logger.info("recommend_api.weather_start")
    weather = get_weather(data.date, data.time, data.place)
    logger.info(
        "recommend_api.weather_done source=%s elapsed_seconds=%.3f",
        weather.get("source"),
        time.perf_counter() - weather_start,
    )

    restaurant_start = time.perf_counter()
    logger.info("recommend_api.kakao_start")
    restaurant_candidates = search_nearby_restaurants(data.place, data.preferences)
    logger.info(
        "recommend_api.kakao_done candidates=%s candidate_names=%s elapsed_seconds=%.3f",
        len(restaurant_candidates),
        [restaurant.get("name") for restaurant in restaurant_candidates[:5]],
        time.perf_counter() - restaurant_start,
    )

    google_start = time.perf_counter()
    logger.info("recommend_api.google_start candidates=%s", len(restaurant_candidates))
    restaurant_candidates = enrich_restaurants_with_google_ratings(restaurant_candidates)
    logger.info(
        "recommend_api.google_done candidates=%s rated=%s elapsed_seconds=%.3f",
        len(restaurant_candidates),
        sum(1 for restaurant in restaurant_candidates if restaurant.get("google_rating") is not None),
        time.perf_counter() - google_start,
    )

    llm_start = time.perf_counter()
    logger.info("recommend_api.menu_start candidates=%s", len(restaurant_candidates))
    menu_result = recommend_menus_with_weather(
        date=data.date,
        time=data.time,
        place=data.place,
        people_count=data.people_count,
        preferences=data.preferences,
        avoid_foods=data.avoid_foods,
        budget=data.budget,
        weather=weather,
        restaurant_candidates=restaurant_candidates,
    )
    menus = menu_result["menus"]
    logger.info(
        "recommend_api.menu_done source=%s menus=%s menu_names=%s elapsed_seconds=%.3f",
        menu_result.get("source", "fallback"),
        len(menus),
        [menu.get("name") for menu in menus],
        time.perf_counter() - llm_start,
    )

    match_start = time.perf_counter()
    logger.info("recommend_api.restaurant_match_start menus=%s candidates=%s", len(menus), len(restaurant_candidates))
    restaurants = match_restaurants_to_menus(restaurant_candidates, menus, data.preferences)
    logger.info(
        "recommend_api.restaurant_match_done restaurants=%s restaurant_names=%s elapsed_seconds=%.3f",
        len(restaurants),
        [restaurant.get("name") for restaurant in restaurants],
        time.perf_counter() - match_start,
    )

    reason_start = time.perf_counter()
    logger.info("recommend_api.restaurant_reason_start restaurants=%s", len(restaurants))
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
    logger.info(
        "recommend_api.restaurant_reason_done restaurants=%s elapsed_seconds=%.3f",
        len(restaurants),
        time.perf_counter() - reason_start,
    )

    result = {
        "input": _request_to_input_dict(data),
        "weather": weather,
        "menus": menus,
        "restaurants": restaurants,
    }
    logger.info(
        "recommend_api.done menus=%s restaurants=%s elapsed_seconds=%.3f",
        len(menus),
        len(restaurants),
        time.perf_counter() - start,
    )
    return result
