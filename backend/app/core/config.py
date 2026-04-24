from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="INFOHOUND_",
        extra="ignore",
    )

    app_name: str = "InfoHound"
    env: str = "development"
    database_url: str = "sqlite:///./data/infohound.db"
    source_config_path: str = "backend/config/sources.yaml"
    raw_storage_path: str = "./data/raw"
    export_path: str = "./data/exports"
    daily_crawl_hour: int = 2
    daily_crawl_minute: int = 0
    scheduler_timezone: str = "Asia/Shanghai"
    http_timeout_seconds: int = 20
    http_retry_count: int = 2
    http_retry_backoff_seconds: float = 1.0
    source_timeout_seconds: int = 180
    max_links_per_source: int = 30

    @property
    def source_config_file(self) -> Path:
        return (ROOT_DIR / self.source_config_path).resolve()

    @property
    def raw_storage_dir(self) -> Path:
        return (ROOT_DIR / self.raw_storage_path).resolve()

    @property
    def export_dir(self) -> Path:
        return (ROOT_DIR / self.export_path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
