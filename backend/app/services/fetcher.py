from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.app.core.config import get_settings
from backend.app.models import Source
from backend.app.services.types import FetchResult


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; InfoHoundBot/0.1; +https://internal.local/infohound)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
}
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


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


def _source_config(source: Source | None) -> dict[str, Any]:
    if source and isinstance(source.config_json, dict):
        return source.config_json
    return {}


def build_client(source: Source | None = None) -> httpx.Client:
    settings = get_settings()
    headers = DEFAULT_HEADERS.copy()
    source_headers = _source_config(source).get("request_headers")
    if isinstance(source_headers, dict):
        headers.update({str(k): str(v) for k, v in source_headers.items()})

    return httpx.Client(
        headers=headers,
        timeout=settings.http_timeout_seconds,
        follow_redirects=True,
    )


def fetch_url(
    client: httpx.Client,
    url: str,
    source: Source | None = None,
    timeout_override: float | None = None,
) -> FetchResult:
    settings = get_settings()
    source_config = _source_config(source)
    default_retry_count = _as_int(getattr(settings, "http_retry_count", 2), 2)
    default_retry_backoff = _as_float(getattr(settings, "http_retry_backoff_seconds", 1.0), 1.0)

    timeout_seconds = max(
        0.1,
        _as_float(
            source_config.get("timeout_seconds", source_config.get("request_timeout_seconds")),
            float(settings.http_timeout_seconds),
        ),
    )
    if timeout_override is not None:
        timeout_seconds = min(timeout_seconds, max(timeout_override, 0.1))

    retries = max(
        0,
        _as_int(
            source_config.get("request_retries", source_config.get("retries")),
            default_retry_count,
        ),
    )
    backoff_seconds = max(
        0.0,
        _as_float(source_config.get("request_retry_backoff_seconds"), default_retry_backoff),
    )
    response: httpx.Response | None = None
    last_exc: Exception | None = None
    timeout = httpx.Timeout(timeout_seconds)

    for attempt in range(retries + 1):
        try:
            response = client.get(url, timeout=timeout)
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < retries:
                delay = backoff_seconds * (attempt + 1)
                logger.warning(
                    "Retrying %s due to status %s (attempt %s/%s)",
                    url,
                    response.status_code,
                    attempt + 1,
                    retries + 1,
                )
                if delay > 0:
                    time.sleep(delay)
                continue

            response.raise_for_status()
            break
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            delay = backoff_seconds * (attempt + 1)
            logger.warning(
                "Retrying %s due to network error %s (attempt %s/%s)",
                url,
                exc.__class__.__name__,
                attempt + 1,
                retries + 1,
            )
            if delay > 0:
                time.sleep(delay)
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status_code = exc.response.status_code
            if status_code in RETRYABLE_STATUS_CODES and attempt < retries:
                delay = backoff_seconds * (attempt + 1)
                logger.warning(
                    "Retrying %s due to HTTP %s (attempt %s/%s)",
                    url,
                    status_code,
                    attempt + 1,
                    retries + 1,
                )
                if delay > 0:
                    time.sleep(delay)
                continue
            raise

    if response is None:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"Failed to fetch url: {url}")

    content_type = response.headers.get("content-type", "").lower()
    content = response.content
    is_pdf = "pdf" in content_type or url.lower().endswith(".pdf") or content[:4] == b"%PDF"
    binary = content if is_pdf else None
    text = None if binary is not None else response.text

    return FetchResult(
        url=url,
        final_url=str(response.url),
        content_type=content_type,
        text=text,
        binary=binary,
        status_code=response.status_code,
    )
