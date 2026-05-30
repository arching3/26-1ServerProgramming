"""Restaurant search module using Kakao Local keyword API."""

from __future__ import annotations

import os
import logging
import time

import requests
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

KAKAO_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
REQUEST_TIMEOUT_SECONDS = 60
logger = logging.getLogger("backend.place")

PREFERENCE_KEYWORDS = {
    "한식": ["한식", "백반", "국밥", "찌개"],
    "중식": ["중식", "중국집", "짜장면", "짬뽕", "탕수육"],
    "일식": ["일식", "초밥", "라멘", "돈카츠", "우동"],
    "양식": ["양식", "파스타", "스테이크", "피자", "브런치"],
}


def _mock_restaurants(place: str, menus: list[dict] | None, size: int) -> list[dict]:
    restaurants = []
    menu_items = menus or [
        {"name": "추천 메뉴", "category": "음식점"},
    ]
    for index, menu in enumerate(menu_items[:size], start=1):
        restaurants.append(
            {
                "name": f"{place} {menu['name']} 전문점",
                "category": f"음식점 > {menu['category']}",
                "address": f"{place} mock 주소 {index}",
                "road_address": f"{place} mock 도로명주소 {index}",
                "phone": "02-0000-0000",
                "place_url": "https://map.kakao.com/",
                "x": "127.027610",
                "y": "37.497942",
                "matched_menu": menu["name"],
            }
        )
    return restaurants


def _call_kakao_keyword(query: str, size: int) -> list[dict]:
    api_key = os.getenv("KAKAO_REST_API_KEY")
    if not api_key:
        raise RuntimeError("KAKAO_REST_API_KEY is missing")

    logger.info("Kakao keyword.start query=%s size=%s timeout=%s", query, size, REQUEST_TIMEOUT_SECONDS)
    start = time.perf_counter()
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query, "size": size}
    try:
        response = requests.get(
            KAKAO_KEYWORD_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        documents = response.json().get("documents", [])
    except Exception:
        logger.exception("Kakao keyword.failed query=%s elapsed_seconds=%.3f", query, time.perf_counter() - start)
        raise
    logger.info(
        "Kakao keyword.done query=%s status=%s documents=%s elapsed_seconds=%.3f",
        query,
        response.status_code,
        len(documents),
        time.perf_counter() - start,
    )
    return documents


def _convert_kakao_place(document: dict, matched_menu: str) -> dict:
    return {
        "name": document.get("place_name", ""),
        "category": document.get("category_name", ""),
        "address": document.get("address_name", ""),
        "road_address": document.get("road_address_name", ""),
        "phone": document.get("phone", ""),
        "place_url": document.get("place_url", ""),
        "x": document.get("x", ""),
        "y": document.get("y", ""),
        "matched_menu": matched_menu,
    }


def _append_unique_restaurants(
    restaurants: list[dict],
    seen_keys: set[str],
    documents: list[dict],
    matched_menu: str,
    size: int,
) -> bool:
    for document in documents:
        restaurant = _convert_kakao_place(document, matched_menu)
        dedupe_key = (
            restaurant.get("place_url")
            or f"{restaurant.get('name')}:{restaurant.get('address')}"
        )
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        restaurants.append(restaurant)
        if len(restaurants) >= size:
            return True
    return False


def _split_preferences(preferences: str) -> list[str]:
    return [item.strip() for item in preferences.split(",") if item.strip()]


def _preference_keywords(preferences: str) -> list[str]:
    keywords = []
    for preference in _split_preferences(preferences):
        keywords.extend(PREFERENCE_KEYWORDS.get(preference, [preference]))
    return list(dict.fromkeys(keywords))


def restaurant_matches_preferences(restaurant: dict, preferences: str) -> bool:
    """Return whether a Kakao restaurant category/name matches food preferences."""
    keywords = _preference_keywords(preferences)
    if not keywords:
        return True

    target = f"{restaurant.get('name', '')} {restaurant.get('category', '')}"
    return any(keyword in target for keyword in keywords)


def _restaurant_preference_score(restaurant: dict, preferences: str) -> int:
    return 1 if restaurant_matches_preferences(restaurant, preferences) else 0


def _build_nearby_queries(place: str, preferences: str) -> list[str]:
    preference_queries = [
        f"{place} {keyword}"
        for keyword in _preference_keywords(preferences)
    ]
    generic_queries = [
        f"{place} 음식점",
        f"{place} 맛집",
        f"{place} 식당",
    ]
    return preference_queries + generic_queries


def search_nearby_restaurants(place: str, preferences: str = "", size: int = 10) -> list[dict]:
    """Search restaurant candidates around a frontend place string."""
    logger.info(
        "nearby restaurants.search_start place=%s preferences=%s size=%s",
        place,
        preferences,
        size,
    )
    start = time.perf_counter()
    restaurants: list[dict] = []
    seen_keys: set[str] = set()
    queries = _build_nearby_queries(place, preferences)

    try:
        for query in queries:
            documents = _call_kakao_keyword(query, size)
            if _append_unique_restaurants(
                restaurants=restaurants,
                seen_keys=seen_keys,
                documents=documents,
                matched_menu="",
                size=size,
            ):
                logger.info(
                    "nearby restaurants.search_done place=%s preferences=%s count=%s elapsed_seconds=%.3f",
                    place,
                    preferences,
                    len(restaurants),
                    time.perf_counter() - start,
                )
                return sorted(
                    restaurants,
                    key=lambda restaurant: _restaurant_preference_score(restaurant, preferences),
                    reverse=True,
                )
    except Exception:
        logger.exception("nearby restaurants.search_failed_using_mock place=%s", place)
        return _mock_restaurants(place, None, size)

    restaurants = sorted(
        restaurants,
        key=lambda restaurant: _restaurant_preference_score(restaurant, preferences),
        reverse=True,
    )
    logger.info(
        "nearby restaurants.search_done place=%s preferences=%s count=%s elapsed_seconds=%.3f",
        place,
        preferences,
        len(restaurants),
        time.perf_counter() - start,
    )
    return restaurants or _mock_restaurants(place, None, size)


def match_restaurants_to_menus(
    restaurants: list[dict],
    menus: list[dict],
    preferences: str = "",
    size: int = 5,
) -> list[dict]:
    """Return Kakao restaurant candidates linked to LLM menu recommendations."""
    logger.info(
        "restaurants.match_start restaurants=%s menus=%s preferences=%s size=%s",
        len(restaurants),
        len(menus),
        preferences,
        size,
    )
    matched = []
    seen_keys = set()

    def normalize_name(value: str) -> str:
        return value.replace(" ", "").lower()

    menu_pairs = [
        (normalize_name(str(menu.get("restaurant_name", ""))), menu)
        for menu in menus
        if menu.get("restaurant_name")
    ]

    sorted_restaurants = sorted(
        restaurants,
        key=lambda restaurant: _restaurant_preference_score(restaurant, preferences),
        reverse=True,
    )

    for restaurant in sorted_restaurants:
        restaurant_name = str(restaurant.get("name", ""))
        normalized_restaurant_name = normalize_name(restaurant_name)
        menu = next(
            (
                menu
                for normalized_menu_name, menu in menu_pairs
                if normalized_menu_name == normalized_restaurant_name
                or normalized_menu_name in normalized_restaurant_name
                or normalized_restaurant_name in normalized_menu_name
            ),
            None,
        )
        if menu is None:
            continue

        dedupe_key = restaurant.get("place_url") or f"{restaurant_name}:{restaurant.get('address')}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        selected = dict(restaurant)
        selected["matched_menu"] = menu.get("name", "")
        matched.append(selected)
        if len(matched) >= size:
            logger.info("restaurants.match_done count=%s", len(matched))
            return matched

    for restaurant in sorted_restaurants:
        dedupe_key = restaurant.get("place_url") or f"{restaurant.get('name')}:{restaurant.get('address')}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        matched.append(dict(restaurant))
        if len(matched) >= size:
            logger.info("restaurants.match_done count=%s", len(matched))
            return matched

    logger.info("restaurants.match_done count=%s", len(matched[:size]))
    return matched[:size]


def search_restaurants(place: str, menus: list[dict], size: int = 5) -> list[dict]:
    """Search real nearby restaurants using Kakao Local keyword API.

    Search order:
    1. place + restaurant keywords
    2. place + recommended menu/category keywords
    """
    nearby_restaurants = search_nearby_restaurants(place, size=max(size, 10))
    if not menus:
        return nearby_restaurants[:size]

    queries = [
        (f"{place} {menus[0]['name']}", menus[0]["name"]),
        (f"{place} {menus[0]['category']}", menus[0]["name"]),
    ]

    restaurants = nearby_restaurants[:]
    seen_keys = {
        restaurant.get("place_url") or f"{restaurant.get('name')}:{restaurant.get('address')}"
        for restaurant in restaurants
    }

    try:
        for query, matched_menu in queries:
            documents = _call_kakao_keyword(query, size)
            if _append_unique_restaurants(
                restaurants=restaurants,
                seen_keys=seen_keys,
                documents=documents,
                matched_menu=matched_menu,
                size=size,
            ):
                return restaurants[:size]
    except Exception:
        return _mock_restaurants(place, menus, size)

    return restaurants[:size] or _mock_restaurants(place, menus, size)
