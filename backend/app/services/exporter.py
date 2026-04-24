from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Document, Source


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


def _document_payload(document: Document, source_name: str, source_slug: str) -> dict[str, object]:
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
        "publish_time": document.publish_time.isoformat() if document.publish_time else None,
        "crawl_time": document.crawl_time.isoformat(),
        "summary": document.summary or "",
        "keywords": _normalize_keywords(document.keywords_json),
        "author_org": document.author_org,
        "content_text": document.content_text or "",
        "status": document.status,
    }


def export_documents_jsonl(session: Session, limit: int = 1000) -> Path:
    settings = get_settings()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = settings.export_dir / f"documents_{timestamp}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    query = (
        select(Document, Source.name, Source.slug)
        .join(Source, Document.source_id == Source.id)
        .order_by(desc(Document.crawl_time))
        .limit(limit)
    )
    rows = session.execute(query).all()

    with output_path.open("w", encoding="utf-8") as handle:
        for document, source_name, source_slug in rows:
            if not _is_exportable_document(document):
                continue
            payload = _document_payload(document, source_name, source_slug)
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return output_path
