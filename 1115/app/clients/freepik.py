import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def fetch_visual_asset(query: str) -> Optional[str]:
    if not settings.freepic_api_key:
        logger.warning("FREEPIC_API_KEY missing; skipping Freepik search.")
        return None

    headers = {"X-API-Key": settings.freepic_api_key, "X-API-Secret": settings.freepic_secret or ""}
    params = {"q": query, "limit": 1}
    endpoint = settings.freepic_base_url

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(endpoint, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Freepik search failed: %s", exc)
        return None

    # Adjust parsing as needed once real payload shape is known.
    first_item = (data.get("data") or [{}])[0]
    preview = first_item.get("images", {}).get("preview")
    return preview
