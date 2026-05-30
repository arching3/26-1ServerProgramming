"""Rule-based menu recommendation fallback helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger("backend.recommendation.fallback")


def contains_any(text: str, keywords: list[str]) -> bool:
    logger.info("contains_any.start text_chars=%s keywords=%s", len(text), len(keywords))
    normalized = text.replace(" ", "").lower()
    matched = any(keyword.replace(" ", "").lower() in normalized for keyword in keywords)
    logger.info("contains_any.done matched=%s", matched)
    return matched


def filter_avoided(menus: list[dict], avoid_foods: str) -> list[dict]:
    logger.info("filter_avoided.start menus=%s avoid_foods=%s", len(menus), bool(avoid_foods))
    avoided = [item.strip() for item in avoid_foods.split(",") if item.strip()]
    if not avoided:
        logger.info("filter_avoided.done no_avoided menus=%s", len(menus))
        return menus

    filtered = []
    for menu in menus:
        combined = f"{menu['name']} {menu['category']} {menu['reason']}"
        if not contains_any(combined, avoided):
            filtered.append(menu)
    result = filtered or menus
    logger.info(
        "filter_avoided.done avoided=%s before=%s after=%s used_original=%s",
        len(avoided),
        len(menus),
        len(result),
        not filtered,
    )
    return result


def select_fallback_candidates(preferences: str) -> list[tuple[str, str, str]]:
    if preferences == "중식":
        return [
            ("마라샹궈", "중식", "여러 명이 나눠 먹기 좋고 취향별 재료 선택이 가능합니다."),
            ("짬뽕", "중식", "식사 메뉴로 명확하고 예산 안에서 선택하기 쉽습니다."),
            ("꿔바로우 세트", "중식", "메인과 사이드를 함께 나누기 좋아 모임 식사에 적합합니다."),
        ]
    if preferences == "일식":
        return [
            ("규동 정식", "일식", "빠르게 먹기 좋고 인원별 주문이 쉬운 메뉴입니다."),
            ("돈카츠 정식", "일식", "호불호가 적고 예산을 맞추기 쉬운 든든한 메뉴입니다."),
            ("우동 세트", "일식", "따뜻한 국물과 식사를 함께 할 수 있어 안정적인 선택입니다."),
        ]
    if preferences == "양식":
        return [
            ("파스타", "양식", "여러 사람이 각자 취향에 맞춰 고르기 좋은 메뉴입니다."),
            ("리조또", "양식", "부담 없이 먹기 좋고 대화하기 좋은 식사 메뉴입니다."),
            ("스테이크 플래터", "양식", "모임에서 함께 나누기 좋고 특별한 식사 느낌을 줍니다."),
        ]
    return [
        ("소불고기 정식", "한식", "한식을 선호하고 여러 명이 함께 먹기 좋은 든든한 메뉴입니다."),
        ("김치찌개", "한식", "예산 안에서 함께 먹기 좋고 식사 만족도가 높은 메뉴입니다."),
        ("닭갈비", "한식", "여러 명이 나눠 먹기 좋고 모임 식사에 잘 어울립니다."),
    ]


def build_fallback_weather_reason(weather: dict) -> str:
    condition = weather.get("condition", "")
    temperature = int(weather.get("temperature", 20))
    rain_probability = int(weather.get("rain_probability", 0))

    if rain_probability >= 50 or "비" in condition:
        weather_reason = "비 예보를 고려해 따뜻하거나 나눠 먹기 좋은 메뉴의 우선순위를 높였습니다."
    elif temperature >= 28:
        weather_reason = "더운 날씨를 고려해 부담이 적고 식사 속도가 편한 메뉴를 추천했습니다."
    elif temperature <= 8:
        weather_reason = "추운 날씨를 고려해 따뜻하고 든든한 메뉴를 추천했습니다."
    else:
        weather_reason = "날씨가 무난해 선호 음식 종류와 예산 조건을 우선 반영했습니다."
    logger.info(
        "fallback_weather_reason condition=%s temperature=%s rain_probability=%s",
        condition,
        temperature,
        rain_probability,
    )
    return weather_reason


def attach_fallback_restaurant(menu: dict, restaurant: dict | None) -> None:
    if restaurant is None:
        return

    menu["restaurant_name"] = restaurant.get("name", "")
    rating = restaurant.get("google_rating")
    rating_text = f" Google 평점 {rating}점을 함께 참고했습니다." if rating else ""
    menu["restaurant_reason"] = (
        "Kakao Map 후보 상호명 중 fallback 메뉴와 함께 검토한 곳입니다."
        f"{rating_text}"
    )


def rank_top_three_menus(menus: list[dict]) -> list[dict]:
    for index, menu in enumerate(menus[:3], start=1):
        menu["rank"] = index
    return menus[:3]


def build_fallback_menus(
    preferences: str,
    avoid_foods: str,
    people_count: int,
    weather: dict,
    restaurant_candidates: list[dict] | None,
) -> list[dict]:
    logger.info("fallback_menus.start preferences=%s", preferences)
    candidates = select_fallback_candidates(preferences)
    weather_reason = build_fallback_weather_reason(weather)
    restaurant_candidates = restaurant_candidates or []
    menus = []

    logger.info("fallback_menus.build_start candidates=%s", len(restaurant_candidates))
    for index, (name, category, reason) in enumerate(candidates, start=1):
        menu = {
            "rank": index,
            "name": name,
            "category": category,
            "price_estimate": f"{max(9000, int(30000 / max(people_count, 1)))}원 내외",
            "reason": reason,
            "weather_reason": weather_reason,
            "recommend_score": 97 - (index * 3),
        }
        restaurant = restaurant_candidates[index - 1] if len(restaurant_candidates) >= index else None
        attach_fallback_restaurant(menu, restaurant)
        menus.append(menu)
        logger.info(
            "fallback_menus.menu_added rank=%s name=%s restaurant=%s",
            index,
            name,
            menu.get("restaurant_name", ""),
        )

    menus = filter_avoided(menus, avoid_foods)
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
        logger.info("fallback_menus.padding_added rank=%s", len(menus))

    ranked = rank_top_three_menus(menus)
    logger.info("fallback_menus.done menu_count=%s", len(ranked))
    return ranked
