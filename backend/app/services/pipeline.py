from __future__ import annotations

import logging
import time
from typing import Any
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import CrawlJob, Document, DocumentRaw, Source
from backend.app.services.discovery import discover_links
from backend.app.services.fetcher import build_client, fetch_url
from backend.app.services.parser import parse_fetch_result
from backend.app.services.processor import process_document
from backend.app.services.source_loader import sync_sources
from backend.app.services.utils import ensure_parent, slugify


logger = logging.getLogger(__name__)


def _as_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _source_timeout_seconds(source: Source) -> float:
    settings = get_settings()
    config = source.config_json if isinstance(source.config_json, dict) else {}
    return max(0.0, _as_float(config.get("source_timeout_seconds"), float(settings.source_timeout_seconds)))


def _build_deadline(source: Source) -> float | None:
    timeout_seconds = _source_timeout_seconds(source)
    if timeout_seconds <= 0:
        return None
    return time.monotonic() + timeout_seconds


def _remaining_seconds(deadline: float | None) -> float | None:
    if deadline is None:
        return None
    return max(0.0, deadline - time.monotonic())


def _save_raw_artifacts(source: Source, title: str, html: str | None, text: str, pdf: bytes | None) -> dict[str, str | None]:
    settings = get_settings()
    day_dir = datetime.now(timezone.utc).strftime("%Y%m%d")
    source_dir = settings.raw_storage_dir / source.slug / day_dir
    safe_name = slugify(title)[:60]

    html_path: Path | None = None
    text_path: Path | None = None
    pdf_path: Path | None = None

    if html:
        html_path = source_dir / f"{safe_name}.html"
        ensure_parent(html_path)
        html_path.write_text(html, encoding="utf-8")

    if text:
        text_path = source_dir / f"{safe_name}.txt"
        ensure_parent(text_path)
        text_path.write_text(text, encoding="utf-8")

    if pdf:
        pdf_path = source_dir / f"{safe_name}.pdf"
        ensure_parent(pdf_path)
        pdf_path.write_bytes(pdf)

    return {
        "raw_html_path": str(html_path) if html_path else None,
        "raw_text_path": str(text_path) if text_path else None,
        "pdf_path": str(pdf_path) if pdf_path else None,
    }


def crawl_source(session: Session, source: Source) -> int:
    saved_count = 0
    source_timed_out = False
    seen_urls_in_run: set[str] = set()
    crawl_job = CrawlJob(source_id=source.id, job_type="crawl", status="running")
    session.add(crawl_job)
    session.commit()
    deadline = _build_deadline(source)

    try:
        with build_client(source) as client:
            discovered_links = discover_links(client, source, deadline=deadline)
            crawl_job.discovered_count = len(discovered_links)
            session.commit()

            for item in discovered_links:
                remaining_seconds = _remaining_seconds(deadline)
                if remaining_seconds is not None and remaining_seconds <= 0:
                    source_timed_out = True
                    break
                try:
                    existing_url = session.scalar(select(Document).where(Document.url == item.url))
                    if existing_url is not None:
                        continue

                    fetch_result = fetch_url(
                        client,
                        item.url,
                        source=source,
                        timeout_override=remaining_seconds,
                    )
                    final_url = fetch_result.final_url
                    if final_url in seen_urls_in_run:
                        continue
                    existing_final_url = session.scalar(select(Document).where(Document.url == final_url))
                    if existing_final_url is not None:
                        seen_urls_in_run.add(final_url)
                        continue

                    parsed = parse_fetch_result(fetch_result)
                    processed = process_document(parsed, source)
                    if len(processed.content_text) < 80:
                        continue

                    if processed.url in seen_urls_in_run:
                        continue
                    existing_processed_url = session.scalar(select(Document).where(Document.url == processed.url))
                    if existing_processed_url is not None:
                        seen_urls_in_run.add(processed.url)
                        continue

                    existing_hash = session.scalar(
                        select(Document).where(Document.content_hash == processed.content_hash)
                    )
                    if existing_hash is not None:
                        continue

                    document = Document(
                        source_id=source.id,
                        title=processed.title,
                        url=processed.url,
                        publish_time=processed.publish_time,
                        language=processed.language,
                        doc_type=source.category,
                        summary=processed.summary,
                        content_text=processed.content_text,
                        author_org=processed.author_org,
                        country=source.country,
                        keywords_json=processed.keywords,
                        content_hash=processed.content_hash,
                        status="new",
                    )
                    session.add(document)
                    session.flush()

                    raw_paths = _save_raw_artifacts(
                        source=source,
                        title=processed.title,
                        html=fetch_result.text,
                        text=processed.content_text,
                        pdf=fetch_result.binary,
                    )
                    raw_record = DocumentRaw(
                        document_id=document.id,
                        raw_html_path=raw_paths["raw_html_path"],
                        raw_text_path=raw_paths["raw_text_path"],
                        pdf_path=raw_paths["pdf_path"],
                        raw_metadata_json=processed.metadata,
                    )
                    session.add(raw_record)
                    session.commit()
                    seen_urls_in_run.add(processed.url)
                    saved_count += 1
                except IntegrityError as exc:
                    logger.warning(
                        "Skipped duplicate document for source %s url=%s error=%s",
                        source.slug,
                        item.url,
                        exc.__class__.__name__,
                    )
                    session.rollback()
                    continue
                except Exception as exc:
                    logger.warning("Failed to process link %s for source %s: %s", item.url, source.slug, exc)
                    session.rollback()
                    continue

        crawl_job.status = "success"
        crawl_job.saved_count = saved_count
        if source_timed_out:
            crawl_job.error_message = (
                f"Stopped early because source timeout reached ({_source_timeout_seconds(source):.1f}s)."
            )
        crawl_job.finished_at = datetime.now(timezone.utc)
        session.commit()
        return saved_count
    except Exception as exc:
        crawl_job.status = "failed"
        crawl_job.error_message = str(exc)
        crawl_job.finished_at = datetime.now(timezone.utc)
        session.commit()
        raise


def crawl_all_sources(session: Session, active_only: bool = True) -> int:
    synced_sources = sync_sources(session)
    sources = synced_sources if not active_only else [source for source in synced_sources if source.is_active]

    total_saved = 0
    for source in sources:
        try:
            total_saved += crawl_source(session, source)
        except Exception:
            session.rollback()
            continue
    return total_saved
