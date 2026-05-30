"""Google Places rating enrichment helpers."""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv


load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GOOGLE_PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.rating,"
    "places.userRatingCount"
)

_RATING_CACHE: dict[str, dict] = {}


def _normalize_cache_key(name: str, address: str) -> str:
    return f"{name}|{address}".replace(" ", "").lower()


def _build_search_query(restaurant: dict) -> str:
    name = restaurant.get("name", "")
    address = restaurant.get("road_address") or restaurant.get("address") or ""
    return f"{name} {address}".strip()


def _call_google_text_search(query: str) -> dict | None:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    response = requests.post(
        GOOGLE_PLACES_TEXT_SEARCH_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": GOOGLE_FIELD_MASK,
        },
        json={
            "textQuery": query,
            "languageCode": "ko",
            "regionCode": "KR",
            "maxResultCount": 1,
        },
        timeout=5,
    )
    response.raise_for_status()

    places = response.json().get("places", [])
    if not places:
        return None
    return places[0]


def _convert_google_place(place: dict) -> dict:
    display_name = place.get("displayName") or {}
    return {
        "google_place_id": place.get("id", ""),
        "google_name": display_name.get("text", ""),
        "google_address": place.get("formattedAddress", ""),
        "google_rating": place.get("rating"),
        "google_user_rating_count": place.get("userRatingCount"),
    }


def get_google_rating(restaurant: dict) -> dict:
    """Return Google rating fields for a Kakao restaurant candidate."""
    query = _build_search_query(restaurant)
    if not query:
        return {}

    cache_key = _normalize_cache_key(
        restaurant.get("name", ""),
        restaurant.get("road_address") or restaurant.get("address") or "",
    )
    if cache_key in _RATING_CACHE:
        return _RATING_CACHE[cache_key]

    try:
        place = _call_google_text_search(query)
    except Exception:
        place = None

    rating = _convert_google_place(place) if place else {}
    _RATING_CACHE[cache_key] = rating
    return rating


def enrich_restaurants_with_google_ratings(
    restaurants: list[dict],
    limit: int = 10,
) -> list[dict]:
    """Attach Google rating fields to restaurant candidates when available."""
    enriched = []
    for index, restaurant in enumerate(restaurants):
        selected = dict(restaurant)
        if index < limit:
            selected.update(get_google_rating(selected))
        enriched.append(selected)
    return enriched
