import json
import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def store_json(path: str, payload: Dict) -> Optional[str]:
    if not settings.liquid_metal_api_key:
        logger.warning("LIQUID_METAL_API_KEY missing; skipping SmartBuckets write.")
        return None

    endpoint = f"{settings.smartbuckets_base_url.rstrip('/')}/upload"
    body = {"bucket": settings.smartbucket_name, "path": path, "data": payload}
    headers = {"Authorization": f"Bearer {settings.liquid_metal_api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            resp.raise_for_status()
            return path
    except Exception as exc:
        logger.error("SmartBuckets write failed: %s", exc)
        return None


async def fetch_latest_policy() -> Optional[Dict]:
    if not settings.liquid_metal_api_key:
        return None
    endpoint = f"{settings.smartbuckets_base_url.rstrip('/')}/objects"
    headers = {"Authorization": f"Bearer {settings.liquid_metal_api_key}"}
    params = {"bucket": settings.smartbucket_name, "prefix": "config/", "limit": 1}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(endpoint, headers=headers, params=params)
            resp.raise_for_status()
            objects = resp.json().get("objects", [])
    except Exception as exc:
        logger.error("SmartBuckets list failed: %s", exc)
        return None

    if not objects:
        return None

    latest_path = objects[0].get("path")
    if not latest_path:
        return None
    download_url = f"{settings.smartbuckets_base_url.rstrip('/')}/download"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                download_url, headers=headers, params={"bucket": settings.smartbucket_name, "path": latest_path}
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.error("SmartBuckets download failed: %s", exc)
        return None


async def fetch_recent_metrics(limit: int = 20) -> List[Dict]:
    if not settings.liquid_metal_api_key:
        return []
    endpoint = f"{settings.smartbuckets_base_url.rstrip('/')}/objects"
    headers = {"Authorization": f"Bearer {settings.liquid_metal_api_key}"}
    params = {"bucket": settings.smartbucket_name, "prefix": "metrics/", "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(endpoint, headers=headers, params=params)
            resp.raise_for_status()
            objects = resp.json().get("objects", [])
    except Exception as exc:
        logger.error("SmartBuckets metrics list failed: %s", exc)
        return []

    metrics = []
    download_url = f"{settings.smartbuckets_base_url.rstrip('/')}/download"
    async with httpx.AsyncClient(timeout=10.0) as client:
        for obj in objects:
            path = obj.get("path")
            if not path:
                continue
            try:
                resp = await client.get(
                    download_url, headers=headers, params={"bucket": settings.smartbucket_name, "path": path}
                )
                resp.raise_for_status()
                metrics.append(resp.json())
            except Exception as exc:
                logger.debug("Skipping metrics %s: %s", path, exc)
                continue
    return metrics
