import logging
from typing import List

import httpx

from app.config import settings
from app.models import CompanyInput, LinkupResult

logger = logging.getLogger(__name__)


async def search_company(company: CompanyInput, policy_query: str) -> List[LinkupResult]:
    if not settings.linkup_api_key:
        logger.warning("LINKUP_API_KEY missing; returning empty results.")
        return []

    params = {"q": policy_query, "limit": 10}
    headers = {"Authorization": f"Bearer {settings.linkup_api_key}"}

    url = f"{settings.linkup_base_url.rstrip('/')}/v1/search"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.error("Linkup search failed: %s", exc)
        return []

    results = []
    for item in payload.get("results", [])[: settings.worker_max_concurrency]:
        try:
            results.append(
                LinkupResult(
                    title=item.get("title", "Untitled"),
                    url=item.get("url"),
                    snippet=item.get("snippet", ""),
                    source=item.get("source", "linkup"),
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed result: %s", exc)
            continue
    return results
