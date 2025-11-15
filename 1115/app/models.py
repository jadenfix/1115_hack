from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, HttpUrl


class CompanyInput(BaseModel):
    name: str
    domain: Optional[str] = None
    persona: str = "SDR researching an account"
    notes: Optional[str] = None


class LinkupResult(BaseModel):
    title: str
    url: HttpUrl
    snippet: str
    source: str


class PageExtraction(BaseModel):
    url: HttpUrl
    page_type: str
    icp: Optional[str] = None
    product_lines: List[str] = []
    pain_points: List[str] = []
    signals: List[str] = []
    raw_text_excerpt: str
    usefulness_score: float
    notes: Optional[str] = None


class CompanySnapshot(BaseModel):
    snapshot_id: str
    company: CompanyInput
    created_at: datetime
    policy_version: str
    linkup_results: List[LinkupResult]
    pages: List[PageExtraction]
    brief_md: str
    outreach_message: str
    freepik_asset_url: Optional[str] = None


class BrowsingPolicy(BaseModel):
    version: str = "v1"
    linkup_query_template: str = (
        "research {company_name} {domain} {persona} pricing product lines solutions case studies"
    )
    max_search_results: int = 5
    allowed_domains: List[str] = []
    preferred_paths: List[str] = ["/about", "/pricing", "/solutions", "/product"]
    max_pages_per_domain: int = 4
    min_usefulness_threshold: float = 0.2


class RunMetrics(BaseModel):
    snapshot_id: str
    policy_version: str
    company: CompanyInput
    num_linkup_results: int
    num_pages_visited: int
    num_useful_pages: int
    avg_usefulness: float
    tool_failures: Dict[str, int]


class AgentWindowState(BaseModel):
    slot: int
    url: HttpUrl
    page_type: str
    status: str  # starting, loading, reading, extracting, done, error
    last_action: str
    screenshot_url: Optional[str] = None
    usefulness_score: Optional[float] = None
    updated_at: datetime
