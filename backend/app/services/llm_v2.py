"""LLM service — generates structured executive summaries with primary/fallback providers and retry logic."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


_SYSTEM_PROMPT = """\
You are a senior sales analyst at Rabbitt AI. Given the following \
pre-computed statistics and top revenue rows from sales data, produce a \
strictly-structured JSON response suitable for executive leadership.

RESPONSE FORMAT — return ONLY valid JSON with exactly these keys:
{
  "executive_summary": "2-3 sentence high-level overview with total revenue and key headline",
  "key_trends": ["trend1", "trend2", ...],
  "regional_analysis": "paragraph about regional performance",
  "product_insights": "paragraph about product category performance",
  "anomalies": ["anomaly1", "anomaly2", ...],
  "recommendations": ["rec1", "rec2", "rec3"]
}

RULES:
- Use professional but accessible language
- Include currency formatting ($X,XXX) for revenue figures
- Flag concerning trends (cancellations, declining months)
- Provide 2-4 actionable recommendations
- Do NOT include markdown formatting — plain text in each value
- Return ONLY the JSON object, no other text
"""

_REQUIRED_KEYS = {
    "executive_summary",
    "key_trends",
    "regional_analysis",
    "product_insights",
    "anomalies",
    "recommendations",
}


def _build_user_prompt(stats_json: str, top_rows_csv: str) -> str:
    return (
        "Here are the pre-computed sales analytics and top revenue rows.\n"
        "Generate the structured JSON report now.\n\n"
        f"**Analytics:**\n```json\n{stats_json}\n```\n\n"
        f"**Top 3 rows by revenue:**\n```csv\n{top_rows_csv}\n```"
    )


def _validate_llm_response(text: str) -> dict[str, Any]:
    """Parse and validate LLM output matches required schema."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    parsed = json.loads(cleaned)
    missing = _REQUIRED_KEYS - set(parsed.keys())
    if missing:
        raise ValueError(f"LLM response missing required keys: {missing}")
    return parsed


async def generate_summary(
    stats: dict[str, Any],
    top_rows_csv: str = "",
) -> dict[str, Any]:
    """
    Generate a structured AI summary with primary + fallback provider.
    Returns validated JSON dict with the required schema keys.
    """
    stats_json = json.dumps(stats, indent=2, default=str)
    user_prompt = _build_user_prompt(stats_json, top_rows_csv)

    primary = settings.llm_provider.lower()
    fallback = settings.llm_fallback_provider.lower()

    # Try primary provider
    try:
        result = await _call_with_retry(primary, user_prompt)
        return result
    except Exception as primary_err:
        logger.warning(
            "Primary LLM (%s) failed: %s — trying fallback (%s)",
            primary, primary_err, fallback,
        )

    # Try fallback provider
    try:
        result = await _call_with_retry(fallback, user_prompt)
        return result
    except Exception as fallback_err:
        raise RuntimeError(
            f"Both LLM providers failed. Primary ({primary}): {primary_err}. "
            f"Fallback ({fallback}): {fallback_err}"
        ) from fallback_err


async def _call_with_retry(
    provider: str,
    user_prompt: str,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Call a provider with exponential backoff retries."""
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            delay = 2 ** attempt
            logger.info("Retry %d/%d for %s (backoff %ds)", attempt, max_retries, provider, delay)
            await asyncio.sleep(delay)
        try:
            start = time.perf_counter()
            raw_text = await _dispatch(provider, user_prompt)
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info("LLM %s responded in %.0fms", provider, latency_ms)
            validated = _validate_llm_response(raw_text)
            validated["_meta"] = {
                "provider": provider,
                "latency_ms": round(latency_ms, 1),
            }
            return validated
        except json.JSONDecodeError as err:
            last_err = ValueError(f"LLM returned invalid JSON: {err}")
            logger.warning("LLM %s returned invalid JSON on attempt %d", provider, attempt + 1)
        except Exception as err:
            last_err = err
            logger.warning("LLM %s error on attempt %d: %s", provider, attempt + 1, err)
    raise last_err  # type: ignore[misc]


async def _dispatch(provider: str, user_prompt: str) -> str:
    """Route to the right provider."""
    if provider == "gemini":
        return await _call_gemini(user_prompt)
    elif provider == "groq":
        return await _call_groq(user_prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def _call_gemini(user_prompt: str) -> str:
    """Call Google Gemini API (google-genai SDK)."""
    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError

    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                max_output_tokens=2048,
                temperature=0.3,
            ),
        )
        return response.text
    except ClientError as e:
        if e.code == 429:
            raise RuntimeError(
                "Gemini API rate limit exceeded. Free-tier daily quota exhausted."
            ) from e
        raise


async def _call_groq(user_prompt: str) -> str:
    """Call Groq API (Llama 3.3)."""
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model="llama-3.3-70b-versatile",
        max_tokens=2048,
        temperature=0.3,
    )
    return chat_completion.choices[0].message.content
