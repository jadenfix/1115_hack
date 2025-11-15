import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from temporalio import activity

from app.clients import anthropic_client, browser_use, freepik, linkup, smartbuckets
from app.config import settings
from app import storage
from app.agent_wall import update_window_state
from app.models import AgentWindowState
from app.models import (
    BrowsingPolicy,
    CompanyInput,
    CompanySnapshot,
    LinkupResult,
    PageExtraction,
    RunMetrics,
)

logger = logging.getLogger(__name__)


@activity.defn
async def load_policy() -> BrowsingPolicy:
    stored = await smartbuckets.fetch_latest_policy()
    if stored:
        try:
            return BrowsingPolicy(**stored)
        except Exception as exc:
            logger.warning("Falling back to default policy due to parse error: %s", exc)
    return BrowsingPolicy()


@activity.defn
async def fetch_company_data_from_linkup(company: CompanyInput, policy: BrowsingPolicy) -> List[LinkupResult]:
    query_text = policy.linkup_query_template.format(
        company_name=company.name, domain=company.domain or "", persona=company.persona
    )
    results = await linkup.search_company(company, query_text)
    if policy.allowed_domains:
        filtered = []
        for r in results:
            if any(r.url.host.endswith(domain) for domain in policy.allowed_domains):
                filtered.append(r)
        results = filtered
    return results[: policy.max_search_results]


async def _score_usefulness(page: PageExtraction, persona: str) -> float:
    schema = {"type": "object", "properties": {"usefulness_score": {"type": "number"}}, "required": ["usefulness_score"]}
    prompt = f"""Given the extracted data:\n{page.model_dump_json()}\nRate usefulness 0-1 for persona {persona}."""
    data = await anthropic_client.claude_json_call("Score page usefulness", prompt, schema)
    score = data.get("usefulness_score") if isinstance(data, dict) else None
    try:
        return float(score)
    except Exception:
        return page.usefulness_score if page.usefulness_score else 0.3


@activity.defn
async def browse_and_extract_pages(
    company: CompanyInput, policy: BrowsingPolicy, linkup_results: List[LinkupResult], run_id: str
) -> List[PageExtraction]:
    urls = [res.url for res in linkup_results]
    chosen_urls = browser_use.choose_urls(urls, policy.preferred_paths, policy.max_pages_per_domain)
    extractions: List[PageExtraction] = []
    for slot, url in enumerate(chosen_urls[:9]):
        start_state = AgentWindowState(
            slot=slot,
            url=url,
            page_type="unknown",
            status="starting",
            last_action="Launching browser session",
            screenshot_url="/static/placeholder.png",
            usefulness_score=None,
            updated_at=datetime.utcnow(),
        )
        update_window_state(run_id, start_state)

        raw = await browser_use.extract_page(str(url), company.name)
        loading_state = start_state.model_copy(
            update={
                "status": "extracting",
                "last_action": "Extracting content",
                "updated_at": datetime.utcnow(),
            }
        )
        update_window_state(run_id, loading_state)

        raw_score = raw.get("usefulness_score")
        try:
            base_score = float(raw_score)
        except Exception:
            base_score = 0.3
        page = PageExtraction(
            url=url,
            page_type=raw.get("page_type", "unknown"),
            icp=raw.get("icp"),
            product_lines=raw.get("product_lines", []),
            pain_points=raw.get("pain_points", []),
            signals=raw.get("signals", []),
            raw_text_excerpt=raw.get("raw_text_excerpt", "")[:500],
            usefulness_score=base_score,
            notes=raw.get("notes"),
        )
        page.usefulness_score = await _score_usefulness(page, company.persona)
        extractions.append(page)
        done_state = loading_state.model_copy(
            update={
                "status": "done",
                "last_action": "Extraction completed",
                "usefulness_score": page.usefulness_score,
                "updated_at": datetime.utcnow(),
            }
        )
        update_window_state(run_id, done_state)
    return extractions


@activity.defn
async def build_snapshot_with_claude(
    company: CompanyInput,
    policy: BrowsingPolicy,
    linkup_results: List[LinkupResult],
    page_extractions: List[PageExtraction],
) -> CompanySnapshot:
    schema = {
        "type": "object",
        "properties": {"brief_md": {"type": "string"}, "outreach_message": {"type": "string"}},
        "required": ["brief_md", "outreach_message"],
    }
    prompt = f"""Build a concise research brief and outreach message for {company.name}.
Linkup results: { [r.model_dump() for r in linkup_results] }
Pages: { [p.model_dump() for p in page_extractions] }"""
    claude_output = await anthropic_client.claude_json_call(
        "You are an SDR research assistant. Return JSON.", prompt, schema
    )
    snapshot = CompanySnapshot(
        snapshot_id=str(uuid.uuid4()),
        company=company,
        created_at=datetime.utcnow(),
        policy_version=policy.version,
        linkup_results=linkup_results,
        pages=page_extractions,
        brief_md=claude_output.get("brief_md", f"Snapshot for {company.name}"),
        outreach_message=claude_output.get(
            "outreach_message", f"Hi {company.name}, excited to connect and learn more!"
        ),
        freepik_asset_url=None,
    )
    return snapshot


@activity.defn
async def attach_freepik_visual(snapshot: CompanySnapshot) -> CompanySnapshot:
    asset = await freepik.fetch_visual_asset(query=snapshot.company.name)
    snapshot.freepik_asset_url = asset
    return snapshot


@activity.defn
async def write_snapshot_to_memory(snapshot: CompanySnapshot) -> str:
    path = f"{snapshot.company.name}/snapshots/{snapshot.snapshot_id}.json"
    await smartbuckets.store_json(path, snapshot.model_dump())
    storage.write_json(f"snapshots/{snapshot.snapshot_id}.json", snapshot.model_dump())
    return snapshot.snapshot_id


@activity.defn
async def log_run_metrics(snapshot: CompanySnapshot) -> None:
    threshold = 0.5
    useful_pages = [p for p in snapshot.pages if p.usefulness_score >= threshold]
    metrics = RunMetrics(
        snapshot_id=snapshot.snapshot_id,
        policy_version=snapshot.policy_version,
        company=snapshot.company,
        num_linkup_results=len(snapshot.linkup_results),
        num_pages_visited=len(snapshot.pages),
        num_useful_pages=len(useful_pages),
        avg_usefulness=(
            sum(p.usefulness_score for p in snapshot.pages) / max(len(snapshot.pages), 1)
        ),
        tool_failures={"linkup": 0, "browser_use": 0, "freepik": 0},
    )
    path = f"metrics/{snapshot.snapshot_id}.json"
    await smartbuckets.store_json(path, metrics.model_dump())
    storage.write_json(path, metrics.model_dump())


@activity.defn
async def fetch_recent_metrics_from_memory() -> List[RunMetrics]:
    raw_metrics = await smartbuckets.fetch_recent_metrics(limit=20)
    parsed = []
    for m in raw_metrics:
        try:
            parsed.append(RunMetrics(**m))
        except Exception as exc:
            logger.debug("Skipping malformed metrics: %s", exc)
    return parsed


@activity.defn
async def propose_new_policy_with_claude(
    current_policy: BrowsingPolicy, metrics: List[RunMetrics]
) -> BrowsingPolicy:
    schema = {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "linkup_query_template": {"type": "string"},
            "max_search_results": {"type": "integer"},
            "preferred_paths": {"type": "array", "items": {"type": "string"}},
            "max_pages_per_domain": {"type": "integer"},
            "min_usefulness_threshold": {"type": "number"},
        },
        "required": [
            "version",
            "linkup_query_template",
            "max_search_results",
            "preferred_paths",
            "max_pages_per_domain",
            "min_usefulness_threshold",
        ],
    }
    prompt = (
        "Given the current policy and metrics, propose a new policy tuned for better useful page rate.\n"
        f"Current policy: {current_policy.model_dump_json()}\n"
        f"Metrics: {[m.model_dump() for m in metrics]}"
    )
    output = await anthropic_client.claude_json_call(
        "You adjust crawling policy for SDR research.", prompt, schema
    )
    try:
        version = output.get("version") or f"v{int(current_policy.version.lstrip('v') or '1') + 1}"
        return BrowsingPolicy(
            version=version,
            linkup_query_template=output.get("linkup_query_template", current_policy.linkup_query_template),
            max_search_results=output.get("max_search_results", current_policy.max_search_results),
            allowed_domains=current_policy.allowed_domains,
            preferred_paths=output.get("preferred_paths", current_policy.preferred_paths),
            max_pages_per_domain=output.get("max_pages_per_domain", current_policy.max_pages_per_domain),
            min_usefulness_threshold=output.get("min_usefulness_threshold", current_policy.min_usefulness_threshold),
        )
    except Exception as exc:
        logger.error("Policy proposal failed, returning current policy: %s", exc)
        return current_policy


@activity.defn
async def save_new_policy(policy: BrowsingPolicy) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    path = f"config/browsing_policy_{timestamp}.json"
    await smartbuckets.store_json(path, policy.model_dump())
    latest_alias = "config/browsing_policy_latest.json"
    await smartbuckets.store_json(latest_alias, policy.model_dump())
    storage.write_json(f"policy/{timestamp}.json", policy.model_dump())
    storage.write_json("policy/latest.json", policy.model_dump())
    return policy.version
