"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/lineageforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Application
    app_name: str = "LineageForge"
    app_version: str = "0.1.0"
    debug: bool = False

    # Worker
    worker_timeout: int = 3600  # 1 hour

    # Identity Resolution
    identity_merge_threshold: float = 0.75
    identity_max_candidates: int = 100

    # Expansion
    expansion_max_depth: int = 3
    expansion_max_nodes: int = 1000

    # WikiTree
    wikitree_api_base: str = "https://api.wikitree.com/api.php"
    wikitree_rate_limit: float = 0.5  # seconds between requests


settings = Settings()
