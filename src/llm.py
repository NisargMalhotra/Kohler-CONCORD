"""
KOHLER CONCORD — LLM Abstraction Layer.

Provides a unified interface for LLM calls. Uses the OpenAI client library
which is compatible with OpenAI, Azure OpenAI, and any OpenAI-compatible API.
Token usage is tracked for the efficiency/sustainability dashboard.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import openai

from src.config import EfficiencyStats, settings

logger = logging.getLogger(__name__)

# Global efficiency stats — shared across the application lifetime
efficiency_stats = EfficiencyStats()


def get_client() -> openai.OpenAI:
    """Create an OpenAI-compatible client configured from settings."""
    kwargs: Dict[str, Any] = {"api_key": settings.LLM_API_KEY or "dummy-key"}
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    return openai.OpenAI(**kwargs)


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.1,
    json_mode: bool = False,
    max_tokens: int = 4096,
) -> str:
    """
    Send a chat completion request and return the response text.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        model: Model name override (defaults to settings.LLM_MODEL).
        temperature: Sampling temperature (lower = more deterministic).
        json_mode: If True, request JSON response format from the API.
        max_tokens: Maximum tokens in the response.

    Returns:
        The assistant's response text, or a bracketed error message string.
    """
    client = get_client()
    model = model or settings.LLM_MODEL

    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
        result = response.choices[0].message.content or ""

        # Track token usage for efficiency dashboard
        if response.usage:
            efficiency_stats.total_tokens_used += response.usage.total_tokens
            if model == settings.LLM_MODEL_SMALL:
                efficiency_stats.small_model_calls += 1
            else:
                efficiency_stats.large_model_calls += 1

        return result

    except openai.AuthenticationError:
        logger.error("LLM authentication failed — check LLM_API_KEY in .env")
        return "[Error: Invalid API key. Please check your LLM_API_KEY in .env]"
    except openai.RateLimitError:
        logger.error("LLM rate limit exceeded")
        return "[Error: Rate limit exceeded. Please wait and retry.]"
    except openai.APIConnectionError as e:
        logger.error(f"LLM connection error: {e}")
        return "[Error: Could not connect to LLM API. Check your network and LLM_BASE_URL.]"
    except openai.APIError as e:
        logger.error(f"LLM API error: {e}")
        return f"[LLM API Error: {getattr(e, 'message', str(e))}]"
    except Exception as e:
        logger.error(f"LLM unexpected error: {e}")
        return f"[LLM Error: {str(e)}]"


def chat_json(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Chat completion that parses the response as JSON.

    Falls back to extracting JSON from markdown code blocks if the raw
    response is not valid JSON. Returns a dict with 'error' key on failure.

    Args:
        messages: List of message dicts.
        model: Optional model name override.
        temperature: Sampling temperature.

    Returns:
        Parsed JSON dict, or {"error": "..."} on failure.
    """
    result = chat(messages, model=model, temperature=temperature, json_mode=True)

    # Propagate LLM errors
    if result.startswith("[Error:") or result.startswith("[LLM"):
        return {"error": result}

    # Try direct parse first
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fences
    for prefix in ("```json", "```"):
        if prefix in result:
            try:
                json_str = result.split(prefix, 1)[1].split("```", 1)[0].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                continue

    logger.error(f"Failed to parse JSON from LLM: {result[:300]}")
    return {"error": "Failed to parse LLM response as JSON", "raw": result[:500]}
