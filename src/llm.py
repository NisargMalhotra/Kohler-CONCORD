"""
KOHLER CONCORD — LLM Abstraction Layer.

Provides a unified interface for LLM calls. Uses the OpenAI client library
which is compatible with OpenAI, Azure OpenAI, and any OpenAI-compatible API.
Token usage is tracked for the efficiency/sustainability dashboard.
Includes automatic retry-with-backoff for rate-limited requests.
"""

from __future__ import annotations

import json
import logging
import random
import time
from typing import Any, Dict, List, Optional

import openai

from src.config import EfficiencyStats, settings

logger = logging.getLogger(__name__)

efficiency_stats = EfficiencyStats()


def get_client() -> openai.OpenAI:
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

    for attempt in range(settings.LLM_MAX_RETRIES):
        try:
            response = client.chat.completions.create(**kwargs)
            result = response.choices[0].message.content or ""

            if response.usage:
                efficiency_stats.total_tokens_used += response.usage.total_tokens
                if model == settings.LLM_MODEL_SMALL:
                    efficiency_stats.small_model_calls += 1
                else:
                    efficiency_stats.large_model_calls += 1

            return result

        except openai.RateLimitError as e:
            wait = None
            if hasattr(e, "response") and e.response is not None:
                retry_after = e.response.headers.get("retry-after")
                if retry_after is not None:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        pass
            
            if wait is None:
                wait = settings.LLM_INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1.0)
            else:
                wait += random.uniform(0, 1.0)
                
            logger.warning(
                f"Rate limited (attempt {attempt + 1}/{settings.LLM_MAX_RETRIES}), "
                f"retrying in {wait:.2f}s…"
            )
            if attempt < settings.LLM_MAX_RETRIES - 1:
                time.sleep(wait)
            else:
                logger.error("Rate limit exceeded after all retries")
                return "[Error: Rate limit exceeded. Please wait a moment and retry.]"

        except openai.AuthenticationError:
            logger.error("LLM authentication failed — check LLM_API_KEY in .env")
            return "[Error: Invalid API key. Please check your LLM_API_KEY in .env]"
        except openai.APIConnectionError as err:
            logger.error(f"LLM connection error: {err}")
            return "[Error: Could not connect to LLM API. Check your network and LLM_BASE_URL.]"
        except openai.APIError as err:
            wait = settings.LLM_INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1.0)
            logger.warning(f"API error (attempt {attempt + 1}): {err}")
            if attempt < settings.LLM_MAX_RETRIES - 1:
                time.sleep(wait)
            else:
                return f"[LLM API Error: {getattr(err, 'message', str(err))}]"
        except Exception as err:
            logger.error(f"LLM unexpected error: {err}")
            return f"[LLM Error: {str(err)}]"

    return "[Error: LLM call failed after retries.]"


def chat_json(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    result = chat(messages, model=model, temperature=temperature, json_mode=True)

    if result.startswith("[Error:") or result.startswith("[LLM"):
        return {"error": result}

    try:
        return json.loads(result)
    except json.JSONDecodeError:
        pass

    for prefix in ("```json", "```"):
        if prefix in result:
            try:
                json_str = result.split(prefix, 1)[1].split("```", 1)[0].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                continue

    logger.error(f"Failed to parse JSON from LLM: {result[:300]}")
    return {"error": "Failed to parse LLM response as JSON", "raw": result[:500]}
