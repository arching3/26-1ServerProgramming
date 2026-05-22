"""
LLM prompt and menu recommendation helpers.

The backend API should pass request data as a dictionary and call
`recommend_menu()`.
"""

import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen


KMA_API_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
KMA_MID_LAND_API_URL = "https://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
KMA_MID_TEMPERATURE_API_URL = "https://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa"
KMA_SERVICE_KEY_ENV = "KMA_SERVICE_KEY"
KMA_SERVICE_KEY = ""

LOCATION_GRID = {
    "서울": {"nx": 60, "ny": 127},
    "강남역": {"nx": 61, "ny": 125},
    "홍대": {"nx": 59, "ny": 127},
    "잠실": {"nx": 62, "ny": 126},
    "부산": {"nx": 98, "ny": 76},
    "대구": {"nx": 89, "ny": 90},
    "인천": {"nx": 55, "ny": 124},
    "광주": {"nx": 58, "ny": 74},
    "대전": {"nx": 67, "ny": 100},
}

MID_REGION_CODE = {
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

SKY_TEXT = {
    "1": "맑음",
    "3": "구름많음",
    "4": "흐림",
}

PTY_TEXT = {
    "0": "강수 없음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
}


def build_prompt(request_data: dict) -> str:
    """Create a consistent prompt for the menu recommendation LLM."""
    data = _normalize_request_data(request_data)
    weather_text = _get_weather_text_for_menu(data)

    return f"""
당신은 메뉴 추천 서비스의 AI입니다.
사용자 조건을 보고 음식 메뉴 3개를 추천해주세요.

[사용자 조건]
- 인원: {data["people"]}명
- 1인당 예산: {data["budget"]}원
- 선호 음식 종류: {data["food_type"]}
- 지역: {data["region"]}
- 날짜: {data["date"]}
- 날씨: {weather_text}

[답변 규칙]
- 추천 메뉴는 정확히 3개만 작성합니다.
- 예산과 선호 음식 종류를 최대한 반영합니다.
- 추천 이유에는 반드시 날씨 정보를 포함합니다.
- 실제 식당 이름을 확실히 모르면 식당 이름은 만들지 않습니다.
- 답변은 아래 형식만 사용합니다.

1. 메뉴명 - 추천 이유
2. 메뉴명 - 추천 이유
3. 메뉴명 - 추천 이유
""".strip()


def recommend_menu(request_data: dict) -> dict:
    """
    Return menu recommendations as a dictionary.

    A real LLM API can be connected later in this function.  For now, this
    fallback response lets the frontend/backend team test the service without
    needing an API key.
    """
    data = _normalize_request_data(request_data)
    weather_result = _get_weather_for_menu(data)
    data["weather"] = weather_result
    prompt = build_prompt(data)
    weather_text = _format_weather_for_menu(weather_result)
    menus = _select_fallback_menus(data["budget"], data["food_type"], weather_text)

    recommendations = []
    for index, menu in enumerate(menus, start=1):
        recommendations.append(
            {
                "rank": index,
                "menu": menu,
                "reason": (
                    f"{data['date']} {data['region']} 날씨가 {weather_text}라서 "
                    f"{data['people']}명이 먹기 좋고, 1인당 {data['budget']}원 "
                    "예산에 맞추기 좋습니다."
                ),
            }
        )

    return {
        "status": "success",
        "input": data,
        "weather": weather_result,
        "prompt": prompt,
        "recommendations": recommendations,
    }


def get_weather(request_data: dict) -> dict:
    """
    Return weather data for a location and date using KMA JSON APIs.

    Expected input:
    {
        "location": "강남역",
        "date": "2026-05-23"
    }

    Set the KMA decoded service key in the KMA_SERVICE_KEY environment variable.
    """
    data = _normalize_weather_request_data(request_data)
    service_key = os.getenv(KMA_SERVICE_KEY_ENV) or KMA_SERVICE_KEY

    if not service_key:
        return {
            "status": "error",
            "message": (
                f"{KMA_SERVICE_KEY_ENV} 환경변수 또는 ai.py의 "
                "KMA_SERVICE_KEY에 기상청 API 키를 설정해주세요."
            ),
            "input": data,
        }

    day_gap = _get_day_gap(data["date"])
    if day_gap < 0:
        return {
            "status": "error",
            "message": "과거 날짜의 날씨는 조회할 수 없습니다.",
            "input": data,
        }

    if day_gap <= 2:
        return _get_short_weather(data, service_key)

    if day_gap <= 10:
        return _get_mid_weather(data, service_key, day_gap)

    return {
        "status": "error",
        "message": "기상청 예보는 오늘부터 10일 뒤까지만 조회할 수 있습니다.",
        "input": data,
    }


def _get_short_weather(data: dict, service_key: str) -> dict:
    """Get today to day-after-tomorrow weather from the short forecast API."""
    grid = LOCATION_GRID.get(data["location"])

    if grid is None:
        return {
            "status": "error",
            "message": "단기예보에서 지원하지 않는 위치입니다.",
            "available_locations": list(LOCATION_GRID.keys()),
            "input": data,
        }

    base_date, base_time = _get_latest_base_datetime()
    params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": grid["nx"],
        "ny": grid["ny"],
    }

    result = _request_kma_json(KMA_API_URL, params)
    if result["status"] == "error":
        result["input"] = data
        return result

    items = _extract_kma_items(result["data"])
    weather = _summarize_weather_items(items, data["date"])

    if not weather:
        return {
            "status": "error",
            "message": "해당 날짜의 예보 데이터를 찾지 못했습니다.",
            "input": data,
            "base_date": base_date,
            "base_time": base_time,
        }

    return {
        "status": "success",
        "input": data,
        "base_date": base_date,
        "base_time": base_time,
        "source": "short_forecast",
        "weather": weather,
    }


def _get_mid_weather(data: dict, service_key: str, day_gap: int) -> dict:
    """Get 3 to 10 day weather from the mid forecast JSON APIs."""
    region = MID_REGION_CODE.get(data["location"])

    if region is None:
        return {
            "status": "error",
            "message": "중기예보에서 지원하지 않는 위치입니다.",
            "available_locations": list(MID_REGION_CODE.keys()),
            "input": data,
        }

    tm_fc = _get_latest_mid_tmfc()
    common_params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": 10,
        "dataType": "JSON",
        "tmFc": tm_fc,
    }
    land_result = _request_kma_json(
        KMA_MID_LAND_API_URL,
        {**common_params, "regId": region["land"]},
    )
    temperature_result = _request_kma_json(
        KMA_MID_TEMPERATURE_API_URL,
        {**common_params, "regId": region["temperature"]},
    )

    if land_result["status"] == "error":
        land_result["input"] = data
        return land_result

    if temperature_result["status"] == "error":
        temperature_result["input"] = data
        return temperature_result

    land_items = _extract_kma_items(land_result["data"])
    temperature_items = _extract_kma_items(temperature_result["data"])

    if not land_items or not temperature_items:
        return {
            "status": "error",
            "message": "중기예보 데이터를 찾지 못했습니다.",
            "input": data,
            "tmFc": tm_fc,
        }

    weather = _summarize_mid_weather(
        land_items[0],
        temperature_items[0],
        data["date"],
        day_gap,
    )

    return {
        "status": "success",
        "input": data,
        "tmFc": tm_fc,
        "source": "mid_forecast",
        "weather": weather,
    }


def _normalize_request_data(request_data: dict) -> dict:
    """Fill missing values and convert request fields to expected types."""
    return {
        "people": int(request_data.get("people", 1)),
        "budget": int(request_data.get("budget", 10000)),
        "food_type": str(request_data.get("food_type", "상관없음")).strip(),
        "region": str(request_data.get("region", "현재 위치")).strip(),
        "date": str(request_data.get("date", datetime.now().strftime("%Y-%m-%d"))).strip(),
        "weather": request_data.get("weather"),
    }


def _normalize_weather_request_data(request_data: dict) -> dict:
    """Fill missing weather fields and convert date to YYYYMMDD."""
    today = datetime.now().strftime("%Y%m%d")
    location = str(request_data.get("location", "서울")).strip()
    date = str(request_data.get("date", today)).strip().replace("-", "")

    return {
        "location": location,
        "date": date,
    }


def _get_day_gap(target_date: str) -> int:
    """Return how many days away the target date is from today."""
    today = datetime.now().date()
    target = datetime.strptime(target_date, "%Y%m%d").date()

    return (target - today).days


def _get_latest_base_datetime() -> tuple[str, str]:
    """Return the latest KMA forecast base date and time."""
    now = datetime.now()
    base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
    current_time = now.strftime("%H%M")

    latest_time = None
    for base_time in base_times:
        if current_time >= base_time:
            latest_time = base_time

    if latest_time is None:
        yesterday = now - timedelta(days=1)
        return yesterday.strftime("%Y%m%d"), "2300"

    return now.strftime("%Y%m%d"), latest_time


def _get_latest_mid_tmfc() -> str:
    """Return the latest mid forecast announcement time."""
    now = datetime.now()
    current_time = now.strftime("%H%M")

    if current_time >= "1800":
        return now.strftime("%Y%m%d") + "1800"

    if current_time >= "0600":
        return now.strftime("%Y%m%d") + "0600"

    yesterday = now - timedelta(days=1)
    return yesterday.strftime("%Y%m%d") + "1800"


def _request_kma_json(api_url: str, params: dict) -> dict:
    """Request a KMA API endpoint and return parsed JSON."""
    try:
        url = api_url + "?" + urlencode(params)
        with urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        return {
            "status": "error",
            "message": "기상청 API 호출에 실패했습니다.",
            "detail": str(error),
        }

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") not in [None, "00"]:
        return {
            "status": "error",
            "message": "기상청 API 응답이 정상 상태가 아닙니다.",
            "detail": header,
        }

    return {
        "status": "success",
        "data": data,
    }


def _extract_kma_items(result: dict) -> list[dict]:
    """Extract item list from KMA JSON response."""
    items = (
        result.get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )

    if isinstance(items, dict):
        return [items]

    return items


def _summarize_weather_items(items: list[dict], target_date: str) -> dict:
    """Extract useful weather values from KMA forecast items."""
    selected = {}

    for item in items:
        if item.get("fcstDate") != target_date:
            continue

        category = item.get("category")
        value = item.get("fcstValue")
        fcst_time = item.get("fcstTime")

        if category in ["TMP", "SKY", "PTY", "POP"] and category not in selected:
            selected[category] = {
                "value": value,
                "time": fcst_time,
            }

    if not selected:
        return {}

    return {
        "date": target_date,
        "temperature": _format_weather_value(selected, "TMP", "도"),
        "sky": SKY_TEXT.get(selected.get("SKY", {}).get("value"), "정보 없음"),
        "precipitation": PTY_TEXT.get(selected.get("PTY", {}).get("value"), "정보 없음"),
        "rain_probability": _format_weather_value(selected, "POP", "%"),
    }


def _summarize_mid_weather(
    land_item: dict,
    temperature_item: dict,
    target_date: str,
    day_gap: int,
) -> dict:
    """Extract 3 to 10 day forecast values from mid forecast items."""
    if day_gap <= 7:
        morning_weather = land_item.get(f"wf{day_gap}Am", "정보 없음")
        afternoon_weather = land_item.get(f"wf{day_gap}Pm", "정보 없음")
        morning_rain = land_item.get(f"rnSt{day_gap}Am", "정보 없음")
        afternoon_rain = land_item.get(f"rnSt{day_gap}Pm", "정보 없음")
    else:
        morning_weather = land_item.get(f"wf{day_gap}", "정보 없음")
        afternoon_weather = morning_weather
        morning_rain = land_item.get(f"rnSt{day_gap}", "정보 없음")
        afternoon_rain = morning_rain

    min_temp = temperature_item.get(f"taMin{day_gap}", "정보 없음")
    max_temp = temperature_item.get(f"taMax{day_gap}", "정보 없음")

    return {
        "date": target_date,
        "morning_weather": morning_weather,
        "afternoon_weather": afternoon_weather,
        "morning_rain_probability": _format_percent(morning_rain),
        "afternoon_rain_probability": _format_percent(afternoon_rain),
        "min_temperature": _format_degree(min_temp),
        "max_temperature": _format_degree(max_temp),
    }


def _format_weather_value(selected: dict, category: str, unit: str) -> str:
    """Format a weather value with a unit."""
    value = selected.get(category, {}).get("value")
    if value is None:
        return "정보 없음"

    return f"{value}{unit}"


def _format_percent(value: object) -> str:
    """Format rain probability."""
    if value in [None, "정보 없음"]:
        return "정보 없음"

    return f"{value}%"


def _format_degree(value: object) -> str:
    """Format temperature."""
    if value in [None, "정보 없음"]:
        return "정보 없음"

    return f"{value}도"


def _get_weather_for_menu(data: dict) -> dict:
    """Return given weather data or fetch weather for menu recommendation."""
    if isinstance(data.get("weather"), dict):
        return data["weather"]

    return get_weather(
        {
            "location": data["region"],
            "date": data["date"],
        }
    )


def _get_weather_text_for_menu(data: dict) -> str:
    """Return weather summary text for the LLM prompt."""
    return _format_weather_for_menu(_get_weather_for_menu(data))


def _format_weather_for_menu(weather_result: dict) -> str:
    """Format weather result as a short Korean sentence for menu reasons."""
    if weather_result.get("status") != "success":
        return f"날씨 정보 확인 실패({weather_result.get('message', '원인 알 수 없음')})"

    weather = weather_result.get("weather", {})
    if weather_result.get("source") == "mid_forecast":
        return (
            f"오전 {weather.get('morning_weather', '정보 없음')}, "
            f"오후 {weather.get('afternoon_weather', '정보 없음')}, "
            f"최저 {weather.get('min_temperature', '정보 없음')}, "
            f"최고 {weather.get('max_temperature', '정보 없음')}, "
            f"오전 강수확률 {weather.get('morning_rain_probability', '정보 없음')}, "
            f"오후 강수확률 {weather.get('afternoon_rain_probability', '정보 없음')}"
        )

    return (
        f"{weather.get('sky', '정보 없음')}, "
        f"{weather.get('precipitation', '정보 없음')}, "
        f"기온 {weather.get('temperature', '정보 없음')}, "
        f"강수확률 {weather.get('rain_probability', '정보 없음')}"
    )


def _select_fallback_menus(budget: int, food_type: str, weather_text: str = "") -> list[str]:
    """Choose simple test recommendations before a real LLM is connected."""
    food_type = food_type.strip()

    if "비" in weather_text or "눈" in weather_text or "흐림" in weather_text:
        if food_type == "일식":
            return ["우동", "라멘", "돈카츠"]

        if food_type == "중식":
            return ["짬뽕", "마파두부덮밥", "우육면"]

        return ["김치찌개", "칼국수", "국밥"]

    menu_by_type = {
        "한식": ["김치찌개", "제육볶음", "비빔밥"],
        "중식": ["짜장면", "짬뽕", "마파두부덮밥"],
        "일식": ["돈카츠", "우동", "초밥"],
        "양식": ["파스타", "리조또", "스테이크"],
        "분식": ["떡볶이", "김밥", "라면"],
    }

    if food_type in menu_by_type:
        menus = menu_by_type[food_type]
    else:
        menus = ["김치찌개", "돈카츠", "파스타"]

    if budget < 10000:
        return ["김밥", "라면", "비빔밥"]

    if budget >= 30000 and food_type == "양식":
        return ["스테이크", "파스타", "리조또"]

    return menus
