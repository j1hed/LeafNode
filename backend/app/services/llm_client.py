"""
services/llm_client.py

One client, two backends - both speak the OpenAI-compatible
/v1/chat/completions schema:

  - LM Studio: local inference server (http://localhost:1234/v1),
    used in the original Multilingual Plant Growth Recommendation
    System and Plant Disease Recommandation2.
  - Groq: free-tier hosted API (https://api.groq.com/openai/v1),
    handy when you don't have LM Studio running (e.g. testing from a
    machine without a GPU, or CI).

Switch providers with LLM_PROVIDER=lmstudio|groq in .env - nothing
else in the codebase needs to change.
"""

import json
import logging
import requests

from app import config

logger = logging.getLogger("llm_client")


class LLMError(Exception):
    pass


def _endpoint_and_headers():
    if config.LLM_PROVIDER == "groq":
        if not config.GROQ_API_KEY:
            raise LLMError("LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env")
        url = f"{config.GROQ_BASE_URL}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
        }
        model = config.GROQ_MODEL
        return url, headers, model

    # default: lmstudio
    url = f"{config.LMSTUDIO_BASE_URL}/chat/completions"
    headers = {"Content-Type": "application/json"}
    model = config.LMSTUDIO_MODEL
    return url, headers, model


def chat_completion(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Send a chat completion request to whichever provider is configured.
    Returns the raw text of the assistant's reply.

    Raises LLMError on failure (caller decides whether to fall back to
    a rule-based response).
    """
    url, headers, model = _endpoint_and_headers()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": config.LLM_MAX_TOKENS,
        "stream": False,
    }

    if json_mode:
        # Both LM Studio (with a JSON-capable model) and Groq accept this.
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=config.LLM_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise LLMError(f"Could not reach LLM provider '{config.LLM_PROVIDER}' at {url}: {e}")

    if response.status_code != 200:
        raise LLMError(f"LLM provider returned {response.status_code}: {response.text[:500]}")

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise LLMError(f"Unexpected LLM response format: {e}")


def current_provider_info() -> dict:
    url, _, model = _endpoint_and_headers() if _safe_config() else (None, None, None)
    return {
        "provider": config.LLM_PROVIDER,
        "model": model,
        "endpoint": url,
    }


def _safe_config() -> bool:
    try:
        _endpoint_and_headers()
        return True
    except LLMError:
        return False


def test_connection() -> dict:
    """Lightweight connectivity check used by /api/system/llm-status."""
    try:
        reply = chat_completion(
            system_prompt="You are a connectivity test.",
            user_prompt="Reply with exactly: OK",
        )
        return {"ok": True, "provider": config.LLM_PROVIDER, "reply": reply.strip()[:100]}
    except LLMError as e:
        return {"ok": False, "provider": config.LLM_PROVIDER, "error": str(e)}
