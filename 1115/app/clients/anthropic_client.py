import json
import logging
from typing import Any, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


ANTHROPIC_MODEL = "claude-3-5-sonnet-latest"


async def claude_json_call(system_prompt: str, user_prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY missing; returning empty JSON for prompt")
        return {}

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "extra_body": {"response_format": {"type": "json_object", "schema": schema}},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Anthropic call failed: %s", exc)
        return {}

    try:
        return json.loads(data["content"][0]["text"])
    except Exception:
        return {}
