import logging
from typing import Dict, List

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def extract_page(url: str, company_name: str) -> Dict:
    """
    Minimal Browser Use API wrapper.

    If no API key is set, returns a stub extraction to keep workflows moving.
    """
    if not settings.browser_use_api_key:
        logger.warning("BROWSER_USE_API_KEY missing; returning stubbed extraction for %s", url)
        return {
            "page_type": "unknown",
            "icp": None,
            "product_lines": [],
            "pain_points": [],
            "signals": [],
            "raw_text_excerpt": f"Stub extraction for {company_name} at {url}",
        }

    payload = {
        "task": f"Visit {url} for {company_name}; extract ICP, product lines, pain points, signals and an excerpt.",
        "url": url,
    }
    headers = {"Authorization": f"Bearer {settings.browser_use_api_key}"}
    endpoint = f"{settings.browser_use_base_url.rstrip('/')}/v1/browse"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.error("Browser Use extraction failed for %s: %s", url, exc)
        return {
            "page_type": "error",
            "icp": None,
            "product_lines": [],
            "pain_points": [],
            "signals": [],
            "raw_text_excerpt": f"Browser Use call failed: {exc}",
        }


def choose_urls(linkup_urls: List[str], preferred_paths: List[str], max_urls: int) -> List[str]:
    chosen: List[str] = []
    for candidate in linkup_urls:
        if len(chosen) >= max_urls:
            break
        if any(path in candidate for path in preferred_paths):
            chosen.append(candidate)
    for candidate in linkup_urls:
        if len(chosen) >= max_urls:
            break
        if candidate not in chosen:
            chosen.append(candidate)
    return chosen
