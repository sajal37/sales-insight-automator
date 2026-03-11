"""LLM service — generates executive summaries via Gemini or Groq."""

from __future__ import annotations

import json
from typing import Any

from app.config import settings

_SYSTEM_PROMPT = """\
You are a senior sales analyst at Rabbitt AI. Given the following \
pre-computed statistics from sales data, write a concise executive \
brief (3-5 paragraphs) suitable for C-suite leadership.

REQUIREMENTS:
- Open with the headline number (total revenue, formatted with currency symbol)
- Highlight top-performing region and product category
- Call out month-over-month trends with percentage changes
- Flag any concerning trends (cancellations, declining revenue months, outliers)
- Close with 2-3 actionable, forward-looking recommendations
- Use professional but accessible language
- Format with **bold** for key figures
- Use markdown headers (##) for sections
"""


def _build_user_prompt(stats_json: str) -> str:
    return (
        "Here are the pre-computed sales statistics. "
        "Write the executive brief now.\n\n"
        f"```json\n{stats_json}\n```"
    )


async def generate_summary(stats: dict[str, Any]) -> str:
    """Generate an AI narrative summary from pre-computed statistics."""
    stats_json = json.dumps(stats, indent=2, default=str)
    user_prompt = _build_user_prompt(stats_json)

    provider = settings.llm_provider.lower()

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
                temperature=0.4,
            ),
        )
        return response.text
    except ClientError as e:
        if e.code == 429:
            raise RuntimeError(
                "Gemini API rate limit exceeded. Your free-tier daily quota is exhausted. "
                "Please wait until tomorrow or upgrade to a paid plan at https://ai.google.dev"
            ) from e
        raise


async def _call_groq(user_prompt: str) -> str:
    """Call Groq API (Llama 3)."""
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model="llama-3.3-70b-versatile",
        max_tokens=2048,
        temperature=0.4,
    )
    return chat_completion.choices[0].message.content
