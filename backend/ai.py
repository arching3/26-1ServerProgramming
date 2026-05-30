"""Compatibility wrapper for recommendation helpers.

New code should import from `backend.recommendation`, but this module keeps the
existing `backend.ai` import path available for the API and older scripts.
"""

from backend.recommendation.fallback import (
    attach_fallback_restaurant as _attach_fallback_restaurant,
    build_fallback_menus as _build_fallback_menus,
    build_fallback_weather_reason as _build_fallback_weather_reason,
    contains_any as _contains_any,
    filter_avoided as _filter_avoided,
    rank_top_three_menus as _rank_top_three_menus,
    select_fallback_candidates as _select_fallback_candidates,
)
from backend.recommendation.menus import (
    GOOGLE_API_KEY,
    LLM_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
    OPENAI_FALLBACK_MODEL,
    ChatGoogleGenerativeAI,
    ChatOpenAI,
    create_llm as _create_llm,
    create_openai_llm as _create_openai_llm,
    is_rate_limit_error,
    normalize_llm_menus as _normalize_llm_menus,
    query,
    recommend_menus_by_llm as _recommend_menus_by_llm,
    recommend_menus_by_openai as _recommend_menus_by_openai,
    recommend_menus_by_provider_chain as _recommend_menus_by_provider_chain,
    recommend_menus_with_llm as _recommend_menus_with_llm,
    recommend_menus_with_weather,
    to_int as _to_int,
)
from backend.recommendation.prompts import (
    MENU_OUTPUT_EXAMPLE,
    build_menu_prompt as _build_menu_prompt,
    format_restaurant_candidate as _format_restaurant_candidate,
    format_restaurant_candidates as _format_restaurant_candidates,
)
from backend.recommendation.reasons import make_restaurant_reason


def _extract_json_text(text: str) -> str:
    """Extract JSON text from a plain string or fenced markdown code block."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


__all__ = [
    "GOOGLE_API_KEY",
    "LLM_TIMEOUT_SECONDS",
    "MENU_OUTPUT_EXAMPLE",
    "OPENAI_API_KEY",
    "OPENAI_FALLBACK_MODEL",
    "ChatGoogleGenerativeAI",
    "ChatOpenAI",
    "is_rate_limit_error",
    "make_restaurant_reason",
    "query",
    "recommend_menus_with_weather",
]
