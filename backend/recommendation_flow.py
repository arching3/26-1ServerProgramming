"""End-to-end menu recommendation workflow."""

from __future__ import annotations

import logging
import time
from typing import Any

from backend.google_places import enrich_restaurants_with_google_ratings
from backend.place import match_restaurants_to_menus, search_nearby_restaurants
from backend.recommendation import make_restaurant_reason, recommend_menus_with_weather
from backend.weather import get_weather

logger = logging.getLogger("backend.recommendation_flow")


def request_to_input_dict(data: Any) -> dict[str, Any]:
    logger.info("request_to_input_dict.start place=%s", data.place)
    result = {
        "date": data.date,
        "time": data.time,
        "place": data.place,
        "people_count": data.people_count,
        "preferences": data.preferences,
        "avoid_foods": data.avoid_foods,
        "budget": data.budget,
    }
    logger.info("request_to_input_dict.done keys=%s", len(result))
    return result


def elapsed(start: float) -> float:
    return time.perf_counter() - start


def restaurant_names(restaurants: list[dict], limit: int = 5) -> list[Any]:
    return [restaurant.get("name") for restaurant in restaurants[:limit]]


def menu_names(menus: list[dict]) -> list[Any]:
    return [menu.get("name") for menu in menus]


def load_weather(data: Any) -> dict:
    start = time.perf_counter()
    logger.info("recommend_api.weather_start")
    weather = get_weather(data.date, data.time, data.place)
    logger.info(
        "recommend_api.weather_done source=%s elapsed_seconds=%.3f",
        weather.get("source"),
        elapsed(start),
    )
    return weather


def load_restaurant_candidates(data: Any) -> list[dict]:
    start = time.perf_counter()
    logger.info("recommend_api.kakao_start")
    restaurant_candidates = search_nearby_restaurants(data.place, data.preferences)
    logger.info(
        "recommend_api.kakao_done candidates=%s candidate_names=%s elapsed_seconds=%.3f",
        len(restaurant_candidates),
        restaurant_names(restaurant_candidates),
        elapsed(start),
    )
    return restaurant_candidates


def enrich_restaurant_candidates(restaurants: list[dict]) -> list[dict]:
    start = time.perf_counter()
    logger.info("recommend_api.google_start candidates=%s", len(restaurants))
    enriched = enrich_restaurants_with_google_ratings(restaurants)
    logger.info(
        "recommend_api.google_done candidates=%s rated=%s elapsed_seconds=%.3f",
        len(enriched),
        sum(1 for restaurant in enriched if restaurant.get("google_rating") is not None),
        elapsed(start),
    )
    return enriched


def recommend_menus(
    data: Any,
    weather: dict,
    restaurant_candidates: list[dict],
) -> list[dict]:
    start = time.perf_counter()
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
        menu_names(menus),
        elapsed(start),
    )
    return menus


def match_restaurants(
    restaurant_candidates: list[dict],
    menus: list[dict],
    preferences: str,
) -> list[dict]:
    start = time.perf_counter()
    logger.info(
        "recommend_api.restaurant_match_start menus=%s candidates=%s",
        len(menus),
        len(restaurant_candidates),
    )
    restaurants = match_restaurants_to_menus(restaurant_candidates, menus, preferences)
    logger.info(
        "recommend_api.restaurant_match_done restaurants=%s restaurant_names=%s elapsed_seconds=%.3f",
        len(restaurants),
        restaurant_names(restaurants, limit=len(restaurants)),
        elapsed(start),
    )
    return restaurants


def attach_selection_reasons(
    restaurants: list[dict],
    data: Any,
    weather: dict,
) -> None:
    start = time.perf_counter()
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
        elapsed(start),
    )


def recommend_menu_flow(data: Any) -> dict:
    """Run the full recommendation flow and return internal response data."""
    logger.info(
        "recommend_api.start place=%s people=%s preferences=%s budget=%s",
        data.place,
        data.people_count,
        data.preferences,
        data.budget,
    )
    start = time.perf_counter()

    weather = load_weather(data)
    restaurant_candidates = load_restaurant_candidates(data)
    restaurant_candidates = enrich_restaurant_candidates(restaurant_candidates)
    menus = recommend_menus(data, weather, restaurant_candidates)
    restaurants = match_restaurants(restaurant_candidates, menus, data.preferences)
    attach_selection_reasons(restaurants, data, weather)

    result = {
        "input": request_to_input_dict(data),
        "weather": weather,
        "menus": menus,
        "restaurants": restaurants,
    }
    logger.info(
        "recommend_api.done menus=%s restaurants=%s elapsed_seconds=%.3f",
        len(menus),
        len(restaurants),
        elapsed(start),
    )
    return result
