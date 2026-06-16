from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import urlparse

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Document, DocumentRaw, Source


AGFUNDER_FEED_OR_HOME_RE = re.compile(r"(^/feed/?$)|(^/$)", re.IGNORECASE)
AGFUNDER_HOME_TITLE_RE = re.compile(r"^(home|homepage|agfunder news|agfundernews)$", re.IGNORECASE)
MARA_BAD_PATH_RE = re.compile(
    r"^/xw/shipin(?:/|$)"
    r"|^/xw/tpxw(?:\d{8})?(?:/|$)"
    r"|^/nybgb/\d{4}/\d{6}/?$",
    re.IGNORECASE,
)
MARA_BREADCRUMB_PREFIX_RE = re.compile(
    r"^(?:当前位置[:：]?\s*.*?(?:\s+|[>＞›/]+\s*)|"
    r"(?:首页|新闻|部门动态|政务动态|工作动态)\s*[>＞›/]+\s*)+",
    re.IGNORECASE,
)
MARA_KEYWORD_NOISE_RE = re.compile(
    r"(?:当前位置|部门动态|政务动态|工作动态|行业动态|新闻资讯|图片新闻|面包屑)",
    re.IGNORECASE,
)
EN_DATE_PATTERN_RE = re.compile(
    r"(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan\.?|Feb\.?|Mar\.?|Apr\.?|May|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)"
    r"\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
NUMERIC_DATE_PATTERN_RE = re.compile(r"(?P<date>\d{1,2}/\d{1,2}/(?:20\d{2}|19\d{2}))")
MODIFIED_HINT_RE = re.compile(r"(last modified|updated|modified)", re.IGNORECASE)


def _normalize_keywords(keywords: list[str] | None) -> list[str]:
    if not keywords:
        return []
    normalized: list[str] = []
    for keyword in keywords:
        if not isinstance(keyword, str):
            continue
        value = keyword.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _clean_cn_mara_summary(summary: str) -> str:
    cleaned = (summary or "").strip()
    cleaned = MARA_BREADCRUMB_PREFIX_RE.sub("", cleaned).strip()
    cleaned = re.sub(
        r"^(?:[>＞›/\s]+|(?:首页|新闻|部门动态|政务动态|工作动态)\s*[>＞›/\s]*)+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned


def _clean_cn_mara_keywords(keywords: list[str]) -> list[str]:
    cleaned: list[str] = []
    for keyword in keywords:
        normalized = keyword.strip()
        if not normalized:
            continue
        if MARA_KEYWORD_NOISE_RE.search(normalized):
            continue
        if normalized in {"新闻", "首页"}:
            continue
        if normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def _raw_metadata_parse_status(raw_metadata: object | None) -> str | None:
    if not isinstance(raw_metadata, dict):
        return None
    parse_status = raw_metadata.get("parse_status")
    if isinstance(parse_status, str):
        return parse_status.strip().lower()
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = str(value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\b([A-Za-z]{3,4})\.\s+", r"\1 ", cleaned)
    for fmt in (
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _extract_publish_time_from_text_head(text: str) -> datetime | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for chunk in lines[:8]:
        en_match = EN_DATE_PATTERN_RE.search(chunk)
        if en_match:
            parsed = _parse_datetime(en_match.group("date"))
            if parsed:
                return parsed
        numeric_match = NUMERIC_DATE_PATTERN_RE.search(chunk)
        if numeric_match and not MODIFIED_HINT_RE.search(chunk):
            parsed = _parse_datetime(numeric_match.group("date"))
            if parsed:
                return parsed
    return None


def _read_publish_time_fallback(document: Document, source_slug: str, raw_text_path: str | None) -> datetime | None:
    if source_slug.lower() != "usda_ars_news":
        return document.publish_time
    if document.publish_time is not None:
        return document.publish_time
    if not raw_text_path:
        return None
    path = Path(raw_text_path)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return _extract_publish_time_from_text_head(text)


def _is_source_noise(document: Document, source_slug: str, raw_metadata: object | None) -> bool:
    url_path = urlparse(document.url or "").path.lower().rstrip("/")
    title = (document.title or "").strip().lower()
    source_slug = source_slug.lower()
    parse_status = _raw_metadata_parse_status(raw_metadata)

    if parse_status == "needs_review":
        return True

    if source_slug == "agfundernews_global":
        if AGFUNDER_FEED_OR_HOME_RE.search(url_path) or "/feed/" in url_path:
            return True
        if not url_path or title in {"home", "homepage", "agfunder news", "agfundernews"}:
            return True

    if source_slug == "cn_mara_news":
        if MARA_BAD_PATH_RE.search(url_path):
            return True

    return False


def _is_exportable_document(document: Document) -> bool:
    content_text = (document.content_text or "").strip()
    summary = (document.summary or "").strip()

    if len(content_text) < 80:
        return False
    if document.title and document.title.strip().lower() in {"untitled", "untitled pdf"} and len(content_text) < 160:
        return False
    if len(summary) < 20 and len(content_text) < 140:
        return False
    return True


def _document_payload(
    document: Document,
    source_name: str,
    source_slug: str,
    raw_text_path: str | None = None,
) -> dict[str, object]:
    publish_time = _read_publish_time_fallback(document, source_slug, raw_text_path)
    summary = document.summary or ""
    keywords = _normalize_keywords(document.keywords_json)
    if source_slug == "cn_mara_news":
        summary = _clean_cn_mara_summary(summary)
        keywords = _clean_cn_mara_keywords(keywords)
    return {
        "id": document.id,
        "source_id": document.source_id,
        "source_slug": source_slug,
        "source": source_name,
        "title": document.title or "",
        "url": document.url,
        "content_hash": document.content_hash,
        "doc_type": document.doc_type,
        "language": document.language,
        "country": document.country,
        "publish_time": publish_time.isoformat() if publish_time else None,
        "crawl_time": document.crawl_time.isoformat(),
        "summary": summary,
        "keywords": keywords,
        "author_org": document.author_org,
        "content_text": document.content_text or "",
        "status": document.status,
    }


def export_documents_jsonl(session: Session, limit: int = 1000) -> Path:
    settings = get_settings()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = settings.export_dir / f"documents_{timestamp}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        if limit <= 0:
            return output_path

        exported_count = 0
        offset = 0
        batch_size = max(limit * 2, 100)

        while exported_count < limit:
            query = (
                select(
                    Document,
                    Source.name,
                    Source.slug,
                    DocumentRaw.raw_metadata_json,
                    DocumentRaw.raw_text_path,
                )
                .join(Source, Document.source_id == Source.id)
                .outerjoin(DocumentRaw, DocumentRaw.document_id == Document.id)
                .order_by(desc(Document.crawl_time))
                .offset(offset)
                .limit(batch_size)
            )
            rows = session.execute(query).all()
            if not rows:
                break

            offset += len(rows)
            for document, source_name, source_slug, raw_metadata_json, raw_text_path in rows:
                if _is_source_noise(document, source_slug, raw_metadata_json):
                    continue
                if not _is_exportable_document(document):
                    continue
                payload = _document_payload(document, source_name, source_slug, raw_text_path)
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                exported_count += 1
                if exported_count >= limit:
                    break

    return output_path
