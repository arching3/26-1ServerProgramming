"""Restaurant recommendation reason builders."""

from __future__ import annotations

import logging

logger = logging.getLogger("backend.recommendation.reasons")


def make_restaurant_reason(
    restaurant: dict,
    matched_menu: str,
    people_count: int,
    budget: str,
    preferences: str,
    avoid_foods: str,
    place: str,
    time: str,
    weather: dict,
) -> str:
    """Create a selection reason from already available restaurant fields."""
    logger.info(
        "make_restaurant_reason.start restaurant=%s matched_menu=%s",
        restaurant.get("name", ""),
        matched_menu,
    )
    name = restaurant.get("name", "해당 음식점")
    category = restaurant.get("category", "")
    address = restaurant.get("road_address") or restaurant.get("address") or place
    weather_summary = weather.get("summary", "날씨 정보를 참고했습니다.")
    google_rating = restaurant.get("google_rating")
    google_user_rating_count = restaurant.get("google_user_rating_count")
    rating_reason = ""
    if google_rating:
        rating_reason = f" Google 평점 {google_rating}점"
        if google_user_rating_count:
            rating_reason += f"과 평가수 {google_user_rating_count}건"
        rating_reason += "도 함께 참고했습니다."

    reason = (
        f"{name}은(는) {matched_menu} 메뉴와 연결해 검토한 음식점입니다. "
        f"카테고리 정보({category})와 위치({address})가 입력한 방문 지역 {place}와 맞고, "
        f"{people_count}명이 {time}에 식사하기 위한 예산({budget}) 조건을 함께 고려했습니다. "
        f"{rating_reason} "
        f"피해야 하는 항목({avoid_foods})은 메뉴 선택 시 제외 대상으로 보며, "
        f"날씨 조건도 함께 반영했습니다: {weather_summary}"
    )
    logger.info("make_restaurant_reason.done chars=%s", len(reason))
    return reason
