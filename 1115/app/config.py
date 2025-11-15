from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Temporal
    temporal_namespace: str = "default"
    temporal_address: str = "temporal:7233"
    temporal_task_queue: str = "research-company"
    worker_max_concurrency: int = 10
    workflow_run_timeout_seconds: int = 600

    # External APIs
    linkup_api_key: Optional[str] = None
    browser_use_api_key: Optional[str] = None
    liquid_metal_api_key: Optional[str] = None
    freepic_api_key: Optional[str] = None
    freepic_secret: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    smartbucket_name: str = "self-evolving-agents-bucket"

    # Optional endpoints
    linkup_base_url: str = "https://api.linkup.so"
    browser_use_base_url: str = "https://api.browser-use.com"
    smartbuckets_base_url: str = "https://api.smartbuckets.ai"
    freepic_base_url: str = "https://api.freepik.com/v1/resources"

    # Service
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_title: str = "Self-Evolving Account Researcher"


settings = Settings()
