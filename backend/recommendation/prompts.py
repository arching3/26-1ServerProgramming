"""Prompt builders for menu recommendation."""

from __future__ import annotations

import json
import logging

try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    ChatPromptTemplate = None

logger = logging.getLogger("backend.recommendation.prompts")

MENU_OUTPUT_EXAMPLE = {
    "menus": [
        {
            "name": "메뉴명",
            "category": "한식",
            "price_estimate": "1인 12000원 내외",
            "reason": "선호와 예산을 반영한 이유",
            "weather_reason": "날씨를 반영한 이유",
            "restaurant_name": "실제 상호명",
            "restaurant_reason": "후보 음식점 중 이 상호명을 고른 이유",
            "recommend_score": 95,
        }
    ]
}


def format_restaurant_candidate(restaurant: dict, place: str) -> str:
    logger.info(
        "format_restaurant_candidate.start name=%s has_rating=%s",
        restaurant.get("name", ""),
        restaurant.get("google_rating") is not None,
    )
    rating = restaurant.get("google_rating")
    rating_count = restaurant.get("google_user_rating_count")
    rating_text = "Google 평점 없음"
    if rating is not None:
        rating_text = f"Google 평점 {rating}"
        if rating_count is not None:
            rating_text += f", 평가수 {rating_count}"

    formatted = (
        f"- {restaurant.get('name', '')} | {restaurant.get('category', '')} | "
        f"{restaurant.get('road_address') or restaurant.get('address') or place} | "
        f"{rating_text}"
    )
    logger.info("format_restaurant_candidate.done chars=%s", len(formatted))
    return formatted


def format_restaurant_candidates(restaurants: list[dict], place: str) -> str:
    restaurant_text = "\n".join(
        format_restaurant_candidate(restaurant, place)
        for restaurant in restaurants[:10]
        if restaurant.get("name")
    )
    return restaurant_text or "후보 없음"


def build_menu_prompt(
    date: str,
    time: str,
    place: str,
    people_count: int,
    preferences: str,
    avoid_foods: str,
    budget: str,
    weather: dict,
    restaurant_candidates: list[dict] | None = None,
):
    """Build a compact prompt for menu recommendation."""
    logger.info(
        "build_menu_prompt.start place=%s people=%s preferences=%s candidates=%s",
        place,
        people_count,
        preferences,
        len(restaurant_candidates or []),
    )
    if ChatPromptTemplate is None:
        raise RuntimeError("langchain_core package is not installed.")

    weather_summary = weather.get("summary", "")
    output_example = json.dumps(MENU_OUTPUT_EXAMPLE, ensure_ascii=False)
    restaurant_candidates = restaurant_candidates or []
    restaurant_text = format_restaurant_candidates(restaurant_candidates, place)
    logger.info(
        "build_menu_prompt.data place=%s candidates=%s restaurant_text_chars=%s output_example_chars=%s",
        place,
        len(restaurant_candidates),
        len(restaurant_text),
        len(output_example),
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 메뉴 추천 AI다. 메뉴 3개를 JSON으로만 추천한다. "
                "식당 상호명은 제공된 Kakao Map 후보에서만 고른다. "
                "후보가 없으면 상호명을 비워둔다.",
            ),
            (
                "human",
                "조건: 날짜={date}, 시간={time}, 장소={place}, 인원={people_count}, "
                "선호={preferences}, 제외={avoid_foods}, 예산={budget}, 날씨={weather_summary}\n"
                "Kakao Map 음식점 후보:\n{restaurant_text}\n"
                "규칙: 선호와 제외 음식을 우선 반영한다. "
                "음식점은 메뉴 적합성을 우선하되, Google 평점과 평가수가 있으면 음식점 선택 근거에 반영한다. "
                "weather_reason에는 반드시 날씨 내용을 넣는다. "
                "restaurant_name은 반드시 후보 줄의 첫 번째 값인 상호명 전체를 글자 하나도 바꾸지 말고 그대로 사용한다. "
                "출력 JSON 형식: {output_example}",
            ),
        ]
    ).partial(
        date=date,
        time=time,
        place=place,
        people_count=people_count,
        preferences=preferences,
        avoid_foods=avoid_foods,
        budget=budget,
        weather_summary=weather_summary,
        restaurant_text=restaurant_text,
        output_example=output_example,
    )
    logger.info("build_menu_prompt.done prompt_type=%s", type(prompt).__name__)
    return prompt
