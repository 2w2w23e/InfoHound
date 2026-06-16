from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from backend.app.core.config import get_settings
from backend.app.models import Source
from backend.app.services.types import DiscoveredLink
from backend.app.services.utils import normalize_url, url_host


RSS_MIME_HINTS = ("xml", "rss", "atom")
XML_START_HINTS = ("<?xml", "<rss", "<feed", "<urlset", "<sitemapindex")
TRACKING_QUERY_KEYS = (
    "utm_",
    "spm",
    "ref",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "_hsmi",
    "_hsenc",
)
NAV_KEYWORDS = {
    "about",
    "contact",
    "privacy",
    "terms",
    "career",
    "careers",
    "jobs",
    "login",
    "signin",
    "signup",
    "register",
    "search",
    "tag",
    "tags",
    "category",
    "categories",
    "topic",
    "topics",
    "author",
    "authors",
    "event",
    "events",
    "video",
    "videos",
    "podcast",
    "podcasts",
}
ASSET_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".zip",
    ".rar",
    ".7z",
    ".mp4",
    ".mp3",
)
LIST_PAGE_MARKERS = (
    "/index.html",
    "/index.htm",
    "/list.html",
    "/list.htm",
    "/channel/",
)
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


def _as_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def _as_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    return fallback


def _matches_patterns(url: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    return any(pattern in url for pattern in patterns)


def _excluded(url: str, patterns: list[str]) -> bool:
    return any(pattern in url for pattern in patterns)


def _extract_xml_links(text: str) -> Iterable[str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    links: list[str] = []
    for item in root.iter():
        if not isinstance(item.tag, str):
            continue
        tag = item.tag.lower()
        if tag.endswith("loc") and item.text:
            links.append(item.text.strip())
            continue
        if tag.endswith("link"):
            if item.text and item.text.strip():
                links.append(item.text.strip())
            href = item.attrib.get("href")
            rel = item.attrib.get("rel", "alternate")
            if href and rel in ("alternate", "self"):
                links.append(href.strip())

    return links


def _is_supported_href(href: str) -> bool:
    lower = href.strip().lower()
    return not lower.startswith(("javascript:", "mailto:", "tel:", "#"))


def _normalize_crawl_type(crawl_type: str) -> str:
    normalized = (crawl_type or "html_list").strip().lower()
    if normalized in {"html_list", "html_list_strict", "rss", "sitemap", "direct"}:
        return normalized
    return "html_list"


def _clean_tracking_query(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url

    filtered = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if any(lowered == hint or lowered.startswith(hint) for hint in TRACKING_QUERY_KEYS):
            continue
        filtered.append((key, value))

    return urlunparse(parsed._replace(query=urlencode(filtered, doseq=True)))


def _canonicalize_source_url(source: Source, url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in {"ars.usda.gov", "www.ars.usda.gov"}:
        return url

    if "/news-events/news/research-news/" not in parsed.path.lower():
        return url

    canonical_host = url_host(source.base_url) or parsed.netloc
    return urlunparse(parsed._replace(scheme="https", netloc=canonical_host))


def _has_article_signal(path: str) -> bool:
    lower_path = path.lower()
    segments = [segment for segment in lower_path.split("/") if segment]
    if not segments:
        return False
    last = segments[-1]
    if last.endswith(".pdf"):
        return True
    if re.search(r"/20\d{2}(?:\d{2})?/", lower_path):
        return True
    if re.search(r"/t20\d{6}_\d+\.htm", lower_path):
        return True
    if any(token in segments for token in ("news", "detail", "article", "story", "press-releases")):
        return True
    if "-" in last and len(last) >= 12:
        return True
    return False


def _looks_like_navigation(path: str, anchor_text: str) -> bool:
    segments = [segment for segment in path.lower().split("/") if segment]
    if not segments:
        return True
    if any(segment in NAV_KEYWORDS for segment in segments):
        return True
    text = anchor_text.strip().lower()
    if text and len(text) <= 3:
        return True
    return False


def _is_useful_link(url: str, crawl_type: str, anchor_text: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in ASSET_EXTENSIONS):
        return False
    if any(marker in path for marker in LIST_PAGE_MARKERS):
        return False
    if re.search(r"/(xw|nybgb)(/20\d{2})?/?$", path):
        return False

    if crawl_type == "html_list_strict":
        if _looks_like_navigation(path, anchor_text) and not _has_article_signal(path):
            return False
        if not _has_article_signal(path) and not parsed.query:
            return False

    if crawl_type == "html_list":
        if _looks_like_navigation(path, anchor_text) and not _has_article_signal(path):
            return False

    return True


def _resolve_timeout(default_timeout: float, deadline: float | None) -> float:
    if deadline is None:
        return default_timeout
    remaining = deadline - time.monotonic()
    return max(0.0, min(default_timeout, remaining))


def discover_links(client: httpx.Client, source: Source, deadline: float | None = None) -> list[DiscoveredLink]:
    settings = get_settings()
    config = source.config_json if isinstance(source.config_json, dict) else {}
    entry_urls = _as_list(config.get("entry_urls"), [source.base_url])
    link_patterns = _as_list(config.get("link_patterns"), [])
    exclude_patterns = _as_list(config.get("exclude_patterns"), [])
    max_links = _as_int(config.get("max_links"), settings.max_links_per_source)
    request_timeout_seconds = _as_float(
        config.get("timeout_seconds", config.get("request_timeout_seconds")),
        float(settings.http_timeout_seconds),
    )
    same_domain_only = _as_bool(config.get("same_domain_only"), True)
    crawl_type = _normalize_crawl_type(source.crawl_type)
    allowed_host = url_host(source.base_url)

    seen: set[str] = set()
    discovered: list[DiscoveredLink] = []

    if crawl_type == "direct":
        for entry_url in entry_urls:
            normalized = _canonicalize_source_url(
                source,
                _clean_tracking_query(normalize_url(source.base_url, entry_url)),
            )
            if normalized in seen:
                continue
            seen.add(normalized)
            discovered.append(DiscoveredLink(url=normalized, source_url=entry_url))
            if len(discovered) >= max_links:
                break
        return discovered

    for entry_url in entry_urls:
        timeout_seconds = _resolve_timeout(request_timeout_seconds, deadline)
        if timeout_seconds <= 0:
            logger.warning("Source %s timed out during discovery", source.slug)
            break

        try:
            response = client.get(entry_url, follow_redirects=True, timeout=timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to discover from %s: %s", entry_url, exc)
            continue

        content_type = response.headers.get("content-type", "").lower()
        body = response.text
        starts_with_xml = body.lstrip().lower().startswith(XML_START_HINTS)
        is_rss = any(hint in content_type for hint in RSS_MIME_HINTS) or starts_with_xml
        xml_mode = crawl_type in {"rss", "sitemap"} or is_rss
        candidate_links: list[tuple[str, str]] = []

        if xml_mode:
            candidate_links.extend((link, "") for link in _extract_xml_links(body))
        else:
            soup = BeautifulSoup(body, "html.parser")
            for anchor in soup.select("a[href]"):
                candidate_links.append((anchor.get("href", ""), anchor.get_text(" ", strip=True)))

        for href, anchor_text in candidate_links:
            if not href:
                continue
            if not _is_supported_href(href):
                continue

            normalized = _canonicalize_source_url(
                source,
                _clean_tracking_query(normalize_url(entry_url, href)),
            )
            parsed = urlparse(normalized)
            if parsed.scheme not in ("http", "https"):
                continue
            host = url_host(normalized)
            if same_domain_only and allowed_host and host != allowed_host:
                continue
            if not _is_useful_link(normalized, crawl_type, anchor_text):
                continue
            if _excluded(normalized, exclude_patterns):
                continue
            if not _matches_patterns(normalized, link_patterns):
                continue
            if normalized in seen:
                continue

            seen.add(normalized)
            discovered.append(DiscoveredLink(url=normalized, source_url=entry_url))
            if len(discovered) >= max_links:
                return discovered

    return discovered
