"""
LLM prompt and menu recommendation helpers.

The backend API should pass request data as a dictionary and call
`recommend_menu()`.
"""

from __future__ import annotations

import json
import logging
import os
import time

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    ChatPromptTemplate = None
    JsonOutputParser = None

from dotenv import load_dotenv


load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_TIMEOUT_SECONDS = 60
OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
logger = logging.getLogger("backend.ai")

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


def _create_llm():
    """Create Gemini chat model."""
    if ChatGoogleGenerativeAI is None:
        raise RuntimeError("langchain_google_genai package is not installed.")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY was not found.")

    return ChatGoogleGenerativeAI(
        model = "gemini-2.5-flash",
        temperature=0.2,
        google_api_key=GOOGLE_API_KEY,
        request_timeout=LLM_TIMEOUT_SECONDS,
    )


def _create_openai_llm():
    """Create OpenAI chat model for Gemini fallback."""
    if ChatOpenAI is None:
        raise RuntimeError("langchain_openai package is not installed.")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY was not found.")

    return ChatOpenAI(
        model=OPENAI_FALLBACK_MODEL,
        temperature=0.2,
        api_key=OPENAI_API_KEY,
        timeout=LLM_TIMEOUT_SECONDS,
    )


def query(question : str) -> str:
    logger.info("Gemini query.start chars=%s timeout=%s", len(question), LLM_TIMEOUT_SECONDS)
    start = time.perf_counter()
    llm = _create_llm()
    try:
        res = llm.invoke(question)
    except Exception:
        logger.exception("Gemini query.failed elapsed_seconds=%.3f", time.perf_counter() - start)
        raise
    logger.info("Gemini query.done elapsed_seconds=%.3f", time.perf_counter() - start)
    return res.content
  
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


def _normalize_llm_menus(raw_menus: object, weather: dict) -> list[dict]:
    """Convert Gemini output to the backend menu response format."""
    if isinstance(raw_menus, dict):
        raw_menus = raw_menus.get("menus", [])

    if not isinstance(raw_menus, list):
        raise ValueError("LLM response is not a menu list.")

    weather_summary = weather.get("summary", "날씨 정보를 참고했습니다.")
    menus = []
    for index, item in enumerate(raw_menus[:3], start=1):
        if not isinstance(item, dict):
            continue

        name = str(item.get("name") or item.get("menu") or "").strip()
        category = str(item.get("category") or "기타").strip()
        reason = str(item.get("reason") or "").strip()
        weather_reason = str(item.get("weather_reason") or "").strip()
        restaurant_name = str(item.get("restaurant_name") or item.get("restaurant") or "").strip()
        restaurant_reason = str(item.get("restaurant_reason") or "").strip()

        if not name:
            continue
        if not reason:
            reason = "사용자 조건과 예산을 고려한 추천 메뉴입니다."
        if not weather_reason:
            weather_reason = f"날씨 조건을 함께 반영했습니다: {weather_summary}"
        if weather_summary not in weather_reason:
            weather_reason = f"{weather_reason} 날씨 정보: {weather_summary}"
        if restaurant_name and not restaurant_reason:
            restaurant_reason = "Kakao Map 후보 상호명 중 메뉴와 조건에 맞는 곳입니다."

        menu = {
            "rank": index,
            "name": name,
            "category": category,
            "price_estimate": str(item.get("price_estimate") or "예산 내 선택 가능"),
            "reason": reason,
            "weather_reason": weather_reason,
            "recommend_score": _to_int(item.get("recommend_score"), 97 - index * 3),
        }
        if restaurant_name:
            menu["restaurant_name"] = restaurant_name
            menu["restaurant_reason"] = restaurant_reason
        menus.append(menu)

    if len(menus) != 3:
        raise ValueError("LLM did not return exactly three menus.")

    return menus


def _recommend_menus_with_llm(prompt: str, weather: dict, llm, provider: str) -> list[dict]:
    """Call an LLM through a LangChain chain and parse recommendations."""
    if ChatPromptTemplate is None or JsonOutputParser is None:
        raise RuntimeError("langchain_core package is not installed.")

    logger.info("LLM menu recommendation.start provider=%s", provider)
    start = time.perf_counter()
    chain = prompt | llm | JsonOutputParser()
    try:
        parsed = chain.invoke({})
        menus = _normalize_llm_menus(parsed, weather)
    except Exception:
        logger.exception(
            "LLM menu recommendation.failed provider=%s elapsed_seconds=%.3f",
            provider,
            time.perf_counter() - start,
        )
        raise
    logger.info(
        "LLM menu recommendation.done provider=%s elapsed_seconds=%.3f menu_count=%s",
        provider,
        time.perf_counter() - start,
        len(menus),
    )
    return menus


def _recommend_menus_by_llm(prompt: str, weather: dict) -> list[dict]:
    """Call Gemini and parse recommendations."""
    return _recommend_menus_with_llm(prompt, weather, _create_llm(), "gemini")


def _recommend_menus_by_openai(prompt: str, weather: dict) -> list[dict]:
    """Call OpenAI and parse recommendations."""
    return _recommend_menus_with_llm(
        prompt,
        weather,
        _create_openai_llm(),
        f"openai:{OPENAI_FALLBACK_MODEL}",
    )


def _format_restaurant_candidate(restaurant: dict, place: str) -> str:
    rating = restaurant.get("google_rating")
    rating_count = restaurant.get("google_user_rating_count")
    rating_text = "Google 평점 없음"
    if rating is not None:
        rating_text = f"Google 평점 {rating}"
        if rating_count is not None:
            rating_text += f", 평가수 {rating_count}"

    return (
        f"- {restaurant.get('name', '')} | {restaurant.get('category', '')} | "
        f"{restaurant.get('road_address') or restaurant.get('address') or place} | "
        f"{rating_text}"
    )


def _build_menu_prompt(
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
    """Build a compact prompt for Gemini menu recommendation."""
    if ChatPromptTemplate is None:
        raise RuntimeError("langchain_core package is not installed.")

    weather_summary = weather.get("summary", "")
    output_example = json.dumps(MENU_OUTPUT_EXAMPLE, ensure_ascii=False)
    restaurant_candidates = restaurant_candidates or []
    restaurant_text = "\n".join(
        _format_restaurant_candidate(restaurant, place)
        for restaurant in restaurant_candidates[:10]
        if restaurant.get("name")
    )
    if not restaurant_text:
        restaurant_text = "후보 없음"
    logger.info(
        "LLM prompt.build place=%s candidates=%s restaurant_text_chars=%s output_example_chars=%s",
        place,
        len(restaurant_candidates),
        len(restaurant_text),
        len(output_example),
    )

    return ChatPromptTemplate.from_messages(
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


def _to_int(value: object, default: int) -> int:
    """Convert a value to int, falling back to default."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def recommend_menus_with_weather(
    date: str,
    time: str,
    place: str,
    people_count: int,
    preferences: str,
    avoid_foods: str,
    budget: str,
    weather: dict,
    restaurant_candidates: list[dict] | None = None,
) -> dict:
    """Recommend three menus based on request data and weather.

    Gemini is used first. If the LLM is unavailable or returns invalid JSON,
    the existing rule-based fallback keeps the API response stable.
    """
    try:
        logger.info(
            "recommend_menus.start place=%s people=%s preferences=%s candidates=%s",
            place,
            people_count,
            preferences,
            len(restaurant_candidates or []),
        )
        prompt = _build_menu_prompt(
            date=date,
            time=time,
            place=place,
            people_count=people_count,
            preferences=preferences,
            avoid_foods=avoid_foods,
            budget=budget,
            weather=weather,
            restaurant_candidates=restaurant_candidates,
        )
        try:
            menus = _recommend_menus_by_llm(prompt, weather)
            source = "gemini"
        except Exception:
            logger.exception("recommend_menus.gemini_failed_trying_openai")
            menus = _recommend_menus_by_openai(prompt, weather)
            source = "openai"

        menus = _filter_avoided(menus, avoid_foods)
        if len(menus) >= 3:
            for index, menu in enumerate(menus[:3], start=1):
                menu["rank"] = index
            logger.info("recommend_menus.llm_success source=%s menu_count=%s", source, len(menus[:3]))
            return {"menus": menus[:3], "source": source}
    except Exception:
        logger.exception("recommend_menus.llm_failed_using_fallback")

    logger.info("recommend_menus.fallback_start preferences=%s", preferences)
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

    restaurant_candidates = restaurant_candidates or []
    menus = []
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
        if len(restaurant_candidates) >= index:
            restaurant = restaurant_candidates[index - 1]
            menu["restaurant_name"] = restaurant.get("name", "")
            rating = restaurant.get("google_rating")
            rating_text = f" Google 평점 {rating}점을 함께 참고했습니다." if rating else ""
            menu["restaurant_reason"] = (
                "Kakao Map 후보 상호명 중 fallback 메뉴와 함께 검토한 곳입니다."
                f"{rating_text}"
            )
        menus.append(menu)

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

    logger.info("recommend_menus.fallback_done menu_count=%s", len(menus[:3]))
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
    google_rating = restaurant.get("google_rating")
    google_user_rating_count = restaurant.get("google_user_rating_count")
    rating_reason = ""
    if google_rating:
        rating_reason = f" Google 평점 {google_rating}점"
        if google_user_rating_count:
            rating_reason += f"과 평가수 {google_user_rating_count}건"
        rating_reason += "도 함께 참고했습니다."

    return (
        f"{name}은(는) {matched_menu} 메뉴와 연결해 검토한 음식점입니다. "
        f"카테고리 정보({category})와 위치({address})가 입력한 방문 지역 {place}와 맞고, "
        f"{people_count}명이 {time}에 식사하기 위한 예산({budget}) 조건을 함께 고려했습니다. "
        f"{rating_reason} "
        f"피해야 하는 항목({avoid_foods})은 메뉴 선택 시 제외 대상으로 보며, "
        f"날씨 조건도 함께 반영했습니다: {weather_summary}"
    )
