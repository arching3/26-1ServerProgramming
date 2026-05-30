"""LLM-backed menu recommendation orchestration."""

from __future__ import annotations

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
except ImportError:
    JsonOutputParser = None

from dotenv import load_dotenv

from backend.recommendation.fallback import build_fallback_menus, filter_avoided, rank_top_three_menus
from backend.recommendation.prompts import build_menu_prompt

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_TIMEOUT_SECONDS = 60
OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
logger = logging.getLogger("backend.recommendation.menus")


def _exception_status_code(error: BaseException) -> int | None:
    for attr in ("status_code", "status", "code"):
        value = getattr(error, attr, None)
        if isinstance(value, int):
            return value

    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value
    return None


def is_rate_limit_error(error: BaseException) -> bool:
    """Return whether an exception looks like an HTTP 429 rate-limit error."""
    seen: set[int] = set()
    pending: list[BaseException] = [error]
    while pending:
        current = pending.pop()
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)

        if _exception_status_code(current) == 429:
            return True

        text = f"{type(current).__name__}: {current}".lower()
        if "429" in text or "rate limit" in text or "quota" in text:
            return True

        cause = getattr(current, "__cause__", None)
        context = getattr(current, "__context__", None)
        if isinstance(cause, BaseException):
            pending.append(cause)
        if isinstance(context, BaseException):
            pending.append(context)
        for arg in getattr(current, "args", ()):
            if isinstance(arg, BaseException):
                pending.append(arg)
    return False


def create_llm():
    """Create Gemini chat model."""
    logger.info("create_llm.start provider=gemini model=gemini-2.5-flash")
    if ChatGoogleGenerativeAI is None:
        raise RuntimeError("langchain_google_genai package is not installed.")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY was not found.")

    kwargs = {
        "model": "gemini-2.5-flash",
        "temperature": 0.2,
        "google_api_key": GOOGLE_API_KEY,
        "request_timeout": LLM_TIMEOUT_SECONDS,
        "max_retries": 0,
    }
    try:
        llm = ChatGoogleGenerativeAI(**kwargs)
    except TypeError:
        kwargs.pop("max_retries")
        llm = ChatGoogleGenerativeAI(**kwargs)
    logger.info("create_llm.done provider=gemini timeout=%s", LLM_TIMEOUT_SECONDS)
    return llm


def create_openai_llm():
    """Create OpenAI chat model for Gemini fallback."""
    logger.info("create_openai_llm.start provider=openai model=%s", OPENAI_FALLBACK_MODEL)
    if ChatOpenAI is None:
        raise RuntimeError("langchain_openai package is not installed.")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY was not found.")

    llm = ChatOpenAI(
        model=OPENAI_FALLBACK_MODEL,
        temperature=0.2,
        api_key=OPENAI_API_KEY,
        timeout=LLM_TIMEOUT_SECONDS,
    )
    logger.info("create_openai_llm.done provider=openai timeout=%s", LLM_TIMEOUT_SECONDS)
    return llm


def query(question: str) -> str:
    logger.info("Gemini query.start chars=%s timeout=%s", len(question), LLM_TIMEOUT_SECONDS)
    start = time.perf_counter()
    llm = create_llm()
    try:
        res = llm.invoke(question)
    except Exception:
        logger.exception("Gemini query.failed elapsed_seconds=%.3f", time.perf_counter() - start)
        raise
    logger.info("Gemini query.done elapsed_seconds=%.3f", time.perf_counter() - start)
    return res.content


def to_int(value: object, default: int) -> int:
    """Convert a value to int, falling back to default."""
    logger.info("to_int.start value_type=%s default=%s", type(value).__name__, default)
    try:
        converted = int(value)
    except (TypeError, ValueError):
        logger.info("to_int.done used_default=True result=%s", default)
        return default
    logger.info("to_int.done used_default=False result=%s", converted)
    return converted


def normalize_llm_menus(raw_menus: object, weather: dict) -> list[dict]:
    """Convert LLM output to the backend menu response format."""
    logger.info("normalize_llm_menus.start raw_type=%s", type(raw_menus).__name__)
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
            "recommend_score": to_int(item.get("recommend_score"), 97 - index * 3),
        }
        if restaurant_name:
            menu["restaurant_name"] = restaurant_name
            menu["restaurant_reason"] = restaurant_reason
        menus.append(menu)

    if len(menus) != 3:
        raise ValueError("LLM did not return exactly three menus.")

    logger.info(
        "normalize_llm_menus.done menus=%s menu_names=%s",
        len(menus),
        [menu.get("name") for menu in menus],
    )
    return menus


def recommend_menus_with_llm(prompt: str, weather: dict, llm, provider: str) -> list[dict]:
    """Call an LLM through a LangChain chain and parse recommendations."""
    if JsonOutputParser is None:
        raise RuntimeError("langchain_core package is not installed.")

    logger.info("LLM menu recommendation.start provider=%s", provider)
    start = time.perf_counter()
    chain = prompt | llm | JsonOutputParser()
    try:
        parsed = chain.invoke({})
        menus = normalize_llm_menus(parsed, weather)
    except Exception as exc:
        if provider == "gemini" and is_rate_limit_error(exc):
            logger.warning(
                "LLM menu recommendation.rate_limited provider=%s elapsed_seconds=%.3f",
                provider,
                time.perf_counter() - start,
            )
        else:
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


def recommend_menus_by_llm(prompt: str, weather: dict) -> list[dict]:
    """Call Gemini and parse recommendations."""
    logger.info("recommend_menus_by_llm.start provider=gemini")
    menus = recommend_menus_with_llm(prompt, weather, create_llm(), "gemini")
    logger.info("recommend_menus_by_llm.done menus=%s", len(menus))
    return menus


def recommend_menus_by_openai(prompt: str, weather: dict) -> list[dict]:
    """Call OpenAI and parse recommendations."""
    logger.info("recommend_menus_by_openai.start provider=openai model=%s", OPENAI_FALLBACK_MODEL)
    menus = recommend_menus_with_llm(
        prompt,
        weather,
        create_openai_llm(),
        f"openai:{OPENAI_FALLBACK_MODEL}",
    )
    logger.info("recommend_menus_by_openai.done menus=%s", len(menus))
    return menus


def recommend_menus_by_provider_chain(prompt: str, weather: dict) -> tuple[list[dict], str]:
    try:
        menus = recommend_menus_by_llm(prompt, weather)
        return menus, "gemini"
    except Exception as exc:
        if is_rate_limit_error(exc):
            logger.warning("recommend_menus.gemini_rate_limited_using_openai")
        else:
            logger.exception("recommend_menus.gemini_failed_trying_openai")
        menus = recommend_menus_by_openai(prompt, weather)
        return menus, "openai"


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
    """Recommend three menus based on request data and weather."""
    try:
        logger.info(
            "recommend_menus.start place=%s people=%s preferences=%s candidates=%s",
            place,
            people_count,
            preferences,
            len(restaurant_candidates or []),
        )
        prompt = build_menu_prompt(
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
        menus, source = recommend_menus_by_provider_chain(prompt, weather)
        menus = filter_avoided(menus, avoid_foods)
        if len(menus) >= 3:
            menus = rank_top_three_menus(menus)
            logger.info("recommend_menus.llm_success source=%s menu_count=%s", source, len(menus[:3]))
            return {"menus": menus, "source": source}
    except Exception:
        logger.exception("recommend_menus.llm_failed_using_fallback")

    menus = build_fallback_menus(
        preferences=preferences,
        avoid_foods=avoid_foods,
        people_count=people_count,
        weather=weather,
        restaurant_candidates=restaurant_candidates,
    )
    return {"menus": menus}
