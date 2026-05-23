"""Weather lookup module.

KMA API calls are attempted only when KMA_API_KEY exists. If the key is missing
or the API response cannot be parsed safely, mock weather is returned.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

LOCATION_CODE_MAP = {
    "서울": {"land": "11B00000", "temperature": "11B10101"},
    "강남역": {"land": "11B00000", "temperature": "11B10101"},
    "홍대": {"land": "11B00000", "temperature": "11B10101"},
    "잠실": {"land": "11B00000", "temperature": "11B10101"},
    "부산": {"land": "11H20000", "temperature": "11H20201"},
    "대구": {"land": "11H10000", "temperature": "11H10701"},
    "인천": {"land": "11B00000", "temperature": "11B20201"},
    "광주": {"land": "11F20000", "temperature": "11F20501"},
    "대전": {"land": "11C20000", "temperature": "11C20401"},
}

KMA_LAND_URL = "https://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
KMA_TEMP_URL = "https://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa"


def get_region_codes(place: str) -> dict:
    """Return KMA region codes for the most relevant known location."""
    for key, codes in LOCATION_CODE_MAP.items():
        if key in place:
            return codes
    return LOCATION_CODE_MAP["서울"]


def _forecast_time() -> str:
    """Return a simple recent forecast time for KMA mid forecast calls."""
    today = datetime.now().strftime("%Y%m%d")
    return f"{today}0600"


def call_kma_land_forecast(land_code: str) -> dict:
    """Call KMA mid land forecast API."""
    api_key = os.getenv("KMA_API_KEY")
    if not api_key:
        raise RuntimeError("KMA_API_KEY is missing")

    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 10,
        "dataType": "JSON",
        "regId": land_code,
        "tmFc": _forecast_time(),
    }
    response = requests.get(KMA_LAND_URL, params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def call_kma_temperature_forecast(temp_code: str) -> dict:
    """Call KMA mid temperature forecast API."""
    api_key = os.getenv("KMA_API_KEY")
    if not api_key:
        raise RuntimeError("KMA_API_KEY is missing")

    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 10,
        "dataType": "JSON",
        "regId": temp_code,
        "tmFc": _forecast_time(),
    }
    response = requests.get(KMA_TEMP_URL, params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def _first_item(data: dict[str, Any]) -> dict[str, Any]:
    return data["response"]["body"]["items"]["item"][0]


def parse_weather(
    date: str,
    time: str,
    place: str,
    land_data: dict,
    temp_data: dict,
) -> dict:
    """Parse KMA responses into the internal weather structure."""
    try:
        land_item = _first_item(land_data)
        temp_item = _first_item(temp_data)
        condition = land_item.get("wf3Am") or land_item.get("wf3Pm") or "맑음"
        rain_probability = land_item.get("rnSt3Am") or land_item.get("rnSt3Pm") or 20
        temperature = temp_item.get("taMax3") or temp_item.get("taMin3") or 23

        return {
            "date": date,
            "time": time,
            "place": place,
            "condition": str(condition),
            "temperature": int(float(temperature)),
            "rain_probability": int(float(rain_probability)),
            "summary": f"{place}의 예보는 {condition}, 기온 약 {temperature}도입니다.",
            "source": "KMA_MID_FORECAST",
            "is_mock": False,
        }
    except Exception:
        return get_mock_weather(date, time, place)


def get_mock_weather(date: str, time: str, place: str) -> dict:
    """Return mock weather when real weather cannot be used."""
    return {
        "date": date,
        "time": time,
        "place": place,
        "condition": "맑음",
        "temperature": 23,
        "rain_probability": 20,
        "summary": "맑고 따뜻한 날씨입니다.",
        "source": "MOCK_WEATHER",
        "is_mock": True,
    }


def get_weather(date: str, time: str, place: str) -> dict:
    """Get weather from KMA, falling back to mock weather."""
    try:
        codes = get_region_codes(place)
        land_data = call_kma_land_forecast(codes["land"])
        temp_data = call_kma_temperature_forecast(codes["temperature"])
        return parse_weather(date, time, place, land_data, temp_data)
    except Exception:
        return get_mock_weather(date, time, place)
