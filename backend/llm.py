"""Groq LLM client.

Deliberately talks to Groq's OpenAI-compatible REST endpoint with `requests` rather than
an SDK: one fewer dependency to conflict with LangChain's httpx pin, and one fewer thing
that can break on the morning of a demo.

The LLM is used for exactly two jobs - classifying intent (with structured JSON output)
and writing prose. It never computes a number.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, GROQ_TIMEOUT_SECONDS

log = logging.getLogger(__name__)

# Groq's free tier has a low requests-per-minute cap, and a demo that fires several
# questions in quick succession will trip it. One short retry absorbs that without making
# the user wait noticeably.
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0


class LLMUnavailable(RuntimeError):
    """Raised when Groq cannot be reached or is not configured.

    Callers are expected to catch this and fall back to deterministic behaviour, never to
    surface it to the user as a stack trace.
    """


def is_configured() -> bool:
    return bool(GROQ_API_KEY)


def _post(messages: list[dict[str, str]], **kwargs: Any) -> str:
    if not GROQ_API_KEY:
        raise LLMUnavailable("GROQ_API_KEY is not set")

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": kwargs.pop("temperature", 0.3),
        "max_tokens": kwargs.pop("max_tokens", 900),
        **kwargs,
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                GROQ_BASE_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=GROQ_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise LLMUnavailable(f"could not reach Groq: {exc}") from exc

        if response.status_code == 200:
            try:
                return response.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, ValueError) as exc:
                raise LLMUnavailable(f"unexpected Groq response shape: {exc}") from exc

        # Rate limited: back off and try again. Groq tells us how long to wait.
        if response.status_code == 429 and attempt < MAX_RETRIES:
            wait = _retry_after(response) or RETRY_BACKOFF_SECONDS * (attempt + 1)
            log.info("Groq rate limited; retrying in %.1fs", wait)
            time.sleep(wait)
            continue

        if response.status_code == 401:
            raise LLMUnavailable("Groq rejected the API key (401). Check GROQ_API_KEY.")
        if response.status_code == 404:
            raise LLMUnavailable(
                f"Groq does not know the model {GROQ_MODEL!r}. Check GROQ_MODEL in .env "
                f"against the model list in the Groq console."
            )
        if response.status_code == 429:
            raise LLMUnavailable("Groq rate limit reached (429). Wait a moment.")
        raise LLMUnavailable(f"Groq returned {response.status_code}: {response.text[:200]}")

    raise LLMUnavailable("Groq rate limit reached (429) after retrying.")


def _retry_after(response: requests.Response) -> float | None:
    """Groq sends a Retry-After header on 429. Cap it so a demo never stalls."""
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return min(float(raw), 8.0)
    except ValueError:
        return None


def complete(system: str, user: str, *, temperature: float = 0.3, max_tokens: int = 900) -> str:
    """Free-text completion."""
    return _post(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )


def complete_json(system: str, user: str, *, temperature: float = 0.0) -> dict[str, Any]:
    """Structured completion. Uses Groq's JSON mode so the result is always parseable."""
    raw = _post(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # JSON mode makes this near-impossible, but a demo should not die on "near".
        raise LLMUnavailable(f"model did not return valid JSON: {exc}") from exc
