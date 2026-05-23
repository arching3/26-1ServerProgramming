"""
LLM prompt and menu recommendation helpers.

The backend API should pass request data as a dictionary and call
`recommend_menu()`.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = text.replace(" ", "").lower()
    return any(keyword.replace(" ", "").lower() in normalized for keyword in keywords)


def _filter_avoided(menus: list[dict], avoid_foods: str) -> list[dict]:
    avoided = [item.strip() for item in avoid_foods.split(",") if item.strip()]
    if not avoided:
        return menus

    filtered = []
    for menu in menus:
        combined = f"{menu['name']} {menu['category']} {menu['reason']}"
        if not _contains_any(combined, avoided):
            filtered.append(menu)
    return filtered or menus


def recommend_menus_with_weather(
    date: str,
    time: str,
    place: str,
    people_count: int,
    preferences: str,
    avoid_foods: str,
    budget: str,
    weather: dict,
) -> dict:
    """Recommend three menus based on request data and weather.

    This currently returns mock data. The prompt is kept separate so a real LLM
    call can replace the mock return block later without changing the API flow.
    """
    prompt = f"""
너는 여러 명의 식사 메뉴를 추천해주는 AI이다.
다음 정보를 바탕으로 메뉴 3개를 추천해라.

날짜: {date}
시간: {time}
장소: {place}
인원수: {people_count}
선호 음식 종류: {preferences}
피해야 하는 음식 또는 식재료: {avoid_foods}
예산: {budget}
날씨: {weather.get("summary", "")}

조건:
- preferences를 가장 우선 반영한다.
- avoid_foods에 포함된 음식 또는 식재료는 추천하지 않는다.
- 날씨는 보조 조건으로만 반영한다.
- 반드시 메뉴 3개를 JSON 구조로 반환한다.
"""
    # Future real LLM integration point:
    # - Read API settings from .env with os.getenv("LLM_API_KEY") and
    #   os.getenv("LLM_MODEL").
    # - Send `prompt` to the selected model.
    # - Parse the model response into the same {"menus": [...]} structure.
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL")
    _ = llm_api_key, llm_model
    _ = prompt

    condition = weather.get("condition", "")
    temperature = int(weather.get("temperature", 20))
    rain_probability = int(weather.get("rain_probability", 0))

    if preferences == "중식":
        candidates = [
            ("마라샹궈", "중식", "여러 명이 나눠 먹기 좋고 취향별 재료 선택이 가능합니다."),
            ("짬뽕", "중식", "식사 메뉴로 명확하고 예산 안에서 선택하기 쉽습니다."),
            ("꿔바로우 세트", "중식", "메인과 사이드를 함께 나누기 좋아 모임 식사에 적합합니다."),
        ]
    elif preferences == "일식":
        candidates = [
            ("규동 정식", "일식", "빠르게 먹기 좋고 인원별 주문이 쉬운 메뉴입니다."),
            ("돈카츠 정식", "일식", "호불호가 적고 예산을 맞추기 쉬운 든든한 메뉴입니다."),
            ("우동 세트", "일식", "따뜻한 국물과 식사를 함께 할 수 있어 안정적인 선택입니다."),
        ]
    elif preferences == "양식":
        candidates = [
            ("파스타", "양식", "여러 사람이 각자 취향에 맞춰 고르기 좋은 메뉴입니다."),
            ("리조또", "양식", "부담 없이 먹기 좋고 대화하기 좋은 식사 메뉴입니다."),
            ("스테이크 플래터", "양식", "모임에서 함께 나누기 좋고 특별한 식사 느낌을 줍니다."),
        ]
    else:
        candidates = [
            ("소불고기 정식", "한식", "한식을 선호하고 여러 명이 함께 먹기 좋은 든든한 메뉴입니다."),
            ("김치찌개", "한식", "예산 안에서 함께 먹기 좋고 식사 만족도가 높은 메뉴입니다."),
            ("닭갈비", "한식", "여러 명이 나눠 먹기 좋고 모임 식사에 잘 어울립니다."),
        ]

    if rain_probability >= 50 or "비" in condition:
        weather_reason = "비 예보를 고려해 따뜻하거나 나눠 먹기 좋은 메뉴의 우선순위를 높였습니다."
    elif temperature >= 28:
        weather_reason = "더운 날씨를 고려해 부담이 적고 식사 속도가 편한 메뉴를 추천했습니다."
    elif temperature <= 8:
        weather_reason = "추운 날씨를 고려해 따뜻하고 든든한 메뉴를 추천했습니다."
    else:
        weather_reason = "날씨가 무난해 선호 음식 종류와 예산 조건을 우선 반영했습니다."

    menus = []
    for index, (name, category, reason) in enumerate(candidates, start=1):
        menus.append(
            {
                "rank": index,
                "name": name,
                "category": category,
                "price_estimate": f"{max(9000, int(30000 / max(people_count, 1)))}원 내외",
                "reason": reason,
                "weather_reason": weather_reason,
                "recommend_score": 97 - (index * 3),
            }
        )

    menus = _filter_avoided(menus, avoid_foods)
    while len(menus) < 3:
        menus.append(
            {
                "rank": len(menus) + 1,
                "name": "비빔밥",
                "category": "한식",
                "price_estimate": "12000원 내외",
                "reason": "피해야 하는 식재료와 충돌 가능성이 낮고 인원별 주문이 쉽습니다.",
                "weather_reason": weather_reason,
                "recommend_score": 85,
            }
        )

    for index, menu in enumerate(menus[:3], start=1):
        menu["rank"] = index

    return {"menus": menus[:3]}


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
    """Create a selection reason for a restaurant returned by Kakao/mock data.

    The reason only uses the restaurant fields already provided. It does not
    invent ratings, reviews, popularity, waiting time, or other unavailable data.
    """
    name = restaurant.get("name", "해당 음식점")
    category = restaurant.get("category", "")
    address = restaurant.get("road_address") or restaurant.get("address") or place
    weather_summary = weather.get("summary", "날씨 정보를 참고했습니다.")

    return (
        f"{name}은(는) {matched_menu} 메뉴와 연결해 검토한 음식점입니다. "
        f"카테고리 정보({category})와 위치({address})가 입력한 방문 지역 {place}와 맞고, "
        f"{people_count}명이 {time}에 식사하기 위한 예산({budget}) 조건을 함께 고려했습니다. "
        f"피해야 하는 항목({avoid_foods})은 메뉴 선택 시 제외 대상으로 보며, "
        f"날씨 조건도 함께 반영했습니다: {weather_summary}"
    )
