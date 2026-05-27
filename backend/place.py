"""Restaurant search module using Kakao Local API."""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def _mock_restaurants(place: str, menus: list[dict], size: int) -> list[dict]:
    restaurants = []
    for index, menu in enumerate(menus[:size], start=1):
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


def search_restaurants(place: str, menus: list[dict], size: int = 5) -> list[dict]:
    """Search real nearby restaurants using Kakao Local API.

    Search order:
    1. place + first ranked menu name
    2. place + menu category
    3. place + "맛집"
    """
    if not menus:
        return _mock_restaurants(place, [], size)

    queries = [
        (f"{place} {menus[0]['name']}", menus[0]["name"]),
        (f"{place} {menus[0]['category']}", menus[0]["name"]),
        (f"{place} 맛집", menus[0]["name"]),
    ]

    restaurants = []
    seen_keys = set()

    try:
        for query, matched_menu in queries:
            for document in _call_kakao_keyword(query, size):
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
                    return restaurants
    except Exception:
        return _mock_restaurants(place, menus, size)

    return restaurants or _mock_restaurants(place, menus, size)
