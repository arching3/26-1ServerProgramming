"""Restaurant search module using Kakao Local keyword API."""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

KAKAO_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


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

    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query, "size": size}
    response = requests.get(
        KAKAO_KEYWORD_SEARCH_URL,
        headers=headers,
        params=params,
        timeout=5,
    )
    response.raise_for_status()
    return response.json().get("documents", [])


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


def search_nearby_restaurants(place: str, size: int = 10) -> list[dict]:
    """Search restaurant candidates around a frontend place string."""
    restaurants: list[dict] = []
    seen_keys: set[str] = set()
    queries = [
        f"{place} 음식점",
        f"{place} 맛집",
        f"{place} 식당",
    ]

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
                return restaurants
    except Exception:
        return _mock_restaurants(place, None, size)

    return restaurants or _mock_restaurants(place, None, size)


def match_restaurants_to_menus(
    restaurants: list[dict],
    menus: list[dict],
    size: int = 5,
) -> list[dict]:
    """Return Kakao restaurant candidates linked to LLM menu recommendations."""
    matched = []
    seen_keys = set()

    def normalize_name(value: str) -> str:
        return value.replace(" ", "").lower()

    menu_pairs = [
        (normalize_name(str(menu.get("restaurant_name", ""))), menu)
        for menu in menus
        if menu.get("restaurant_name")
    ]

    for restaurant in restaurants:
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
            return matched

    for restaurant in restaurants:
        dedupe_key = restaurant.get("place_url") or f"{restaurant.get('name')}:{restaurant.get('address')}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        matched.append(dict(restaurant))
        if len(matched) >= size:
            return matched

    return matched[:size]


def search_restaurants(place: str, menus: list[dict], size: int = 5) -> list[dict]:
    """Search real nearby restaurants using Kakao Local keyword API.

    Search order:
    1. place + restaurant keywords
    2. place + recommended menu/category keywords
    """
    nearby_restaurants = search_nearby_restaurants(place, max(size, 10))
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
