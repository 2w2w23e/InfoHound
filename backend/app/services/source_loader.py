from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Source


logger = logging.getLogger(__name__)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        cleaned: list[str] = []
        for item in value:
            if isinstance(item, dict):
                continue
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _as_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _merge_list(*values: Any) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in _as_list(value):
            if item in seen:
                continue
            seen.add(item)
            merged.append(item)
    return merged


def load_source_config(config_path: Path | None = None) -> dict[str, Any]:
    settings = get_settings()
    path = config_path or settings.source_config_file
    if not path.exists():
        return {"defaults": {}, "sources": []}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        logger.exception("Failed to parse source config file: %s", path)
        return {"defaults": {}, "sources": []}

    if isinstance(data, list):
        return {"defaults": {}, "sources": data}
    if not isinstance(data, dict):
        logger.warning("Unexpected source config format in %s", path)
        return {"defaults": {}, "sources": []}

    return {
        "defaults": _as_dict(data.get("defaults")),
        "sources": data.get("sources", []) if isinstance(data.get("sources"), list) else [],
    }


def sync_sources(session: Session) -> list[Source]:
    settings = get_settings()
    config_data = load_source_config()
    configured_sources = config_data.get("sources", [])
    defaults = _as_dict(config_data.get("defaults"))
    default_request = _as_dict(defaults.get("request"))
    default_discovery = _as_dict(defaults.get("discovery"))
    default_crawl = _as_dict(defaults.get("crawl"))
    default_max_links = _as_int(defaults.get("max_links"), settings.max_links_per_source)
    default_timeout_seconds = _as_float(
        defaults.get("timeout_seconds", default_request.get("timeout_seconds", settings.http_timeout_seconds)),
        float(settings.http_timeout_seconds),
    )
    default_same_domain_only = defaults.get(
        "same_domain_only",
        default_discovery.get("same_domain_only", True),
    )
    default_retry_count = _as_int(getattr(settings, "http_retry_count", 2), 2)
    default_retry_backoff = _as_float(getattr(settings, "http_retry_backoff_seconds", 1.0), 1.0)
    default_source_timeout = _as_float(
        getattr(settings, "source_timeout_seconds", 180),
        180.0,
    )
    default_crawl_type = str(defaults.get("crawl_type", "html_list")).strip() or "html_list"
    synced: list[Source] = []

    for item in configured_sources:
        if not isinstance(item, dict):
            continue

        slug = item.get("slug")
        name = item.get("name")
        base_url = item.get("base_url")
        category = item.get("category")
        if not (slug and name and base_url and category):
            logger.warning("Skipped invalid source config item: %s", item)
            continue

        request_config = _as_dict(item.get("request"))
        discovery_config = _as_dict(item.get("discovery"))
        crawl_config = _as_dict(item.get("crawl"))

        request_headers = _as_dict(default_request.get("headers")).copy()
        request_headers.update(_as_dict(item.get("headers")))
        request_headers.update(_as_dict(request_config.get("headers")))

        entry_urls = (
            _as_list(item.get("entry_urls"))
            or _as_list(discovery_config.get("entry_urls"))
            or _as_list(default_discovery.get("entry_urls"))
            or [str(base_url)]
        )
        link_patterns = _merge_list(
            default_discovery.get("link_patterns"),
            discovery_config.get("link_patterns"),
            item.get("link_patterns"),
        )
        exclude_patterns = _merge_list(
            default_discovery.get("exclude_patterns"),
            discovery_config.get("exclude_patterns"),
            item.get("exclude_patterns"),
        )

        max_links = _as_int(
            item.get(
                "max_links",
                discovery_config.get(
                    "max_links",
                    default_discovery.get("max_links", default_max_links),
                ),
            ),
            settings.max_links_per_source,
        )
        timeout_seconds = _as_float(
            item.get(
                "timeout_seconds",
                item.get(
                    "request_timeout_seconds",
                    request_config.get(
                        "timeout_seconds",
                        default_request.get("timeout_seconds", default_timeout_seconds),
                    ),
                ),
            ),
            default_timeout_seconds,
        )
        request_timeout_seconds = _as_float(
            item.get(
                "request_timeout_seconds",
                item.get(
                    "timeout_seconds",
                    request_config.get("timeout_seconds", default_timeout_seconds),
                ),
            ),
            default_timeout_seconds,
        )
        request_retries = _as_int(
            item.get(
                "request_retries",
                request_config.get("retries", default_retry_count),
            ),
            default_retry_count,
        )
        request_retry_backoff_seconds = _as_float(
            item.get(
                "request_retry_backoff_seconds",
                request_config.get("retry_backoff_seconds", default_retry_backoff),
            ),
            default_retry_backoff,
        )
        source_timeout_seconds = _as_float(
            item.get(
                "source_timeout_seconds",
                crawl_config.get(
                    "source_timeout_seconds",
                    default_crawl.get("source_timeout_seconds", default_source_timeout),
                ),
            ),
            default_source_timeout,
        )

        source = session.scalar(select(Source).where(Source.slug == slug))
        if source is None:
            source = Source(slug=slug)
            session.add(source)

        source.name = str(name)
        source.base_url = str(base_url)
        source.category = str(category)
        source.language = item.get("language", "zh")
        source.country = item.get("country", "GLOBAL")
        source.crawl_type = str(item.get("crawl_type", default_crawl_type))
        source.is_active = item.get("is_active", True)
        source.config_json = {
            "entry_urls": entry_urls,
            "link_patterns": link_patterns,
            "exclude_patterns": exclude_patterns,
            "same_domain_only": item.get(
                "same_domain_only",
                discovery_config.get("same_domain_only", default_same_domain_only),
            ),
            "max_links": max_links,
            "timeout_seconds": timeout_seconds,
            "source_timeout_seconds": source_timeout_seconds,
            "request_timeout_seconds": request_timeout_seconds,
            "request_retries": max(0, request_retries),
            "request_retry_backoff_seconds": max(0.0, request_retry_backoff_seconds),
            "request_headers": request_headers,
            "notes": item.get("notes", ""),
        }
        synced.append(source)

    session.commit()
    return synced
