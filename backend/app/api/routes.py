from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.db import get_session
from backend.app.models import Document, Source
from backend.app.schemas import CrawlRunResponse, DocumentRead, SourceRead
from backend.app.services.exporter import export_documents_jsonl
from backend.app.services.pipeline import crawl_all_sources, crawl_source
from backend.app.services.source_loader import sync_sources


router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sources", response_model=list[SourceRead])
def list_sources(session: Session = Depends(get_session)) -> list[Source]:
    return list(session.scalars(select(Source).order_by(Source.category, Source.name)))


@router.post("/sources/sync", response_model=list[SourceRead])
def sync_source_config(session: Session = Depends(get_session)) -> list[Source]:
    return sync_sources(session)


@router.post("/crawl/run", response_model=CrawlRunResponse)
def run_crawl(
    source_slug: str | None = None,
    session: Session = Depends(get_session),
) -> CrawlRunResponse:
    if source_slug:
        source = session.scalar(select(Source).where(Source.slug == source_slug))
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
        saved = crawl_source(session, source)
        return CrawlRunResponse(message="Crawl finished", sources_processed=1, documents_saved=saved)

    saved = crawl_all_sources(session)
    source_count = len(list(session.scalars(select(Source).where(Source.is_active.is_(True)))))
    return CrawlRunResponse(
        message="Crawl finished",
        sources_processed=source_count,
        documents_saved=saved,
    )


@router.get("/documents", response_model=list[DocumentRead])
def list_documents(
    limit: int = Query(default=50, le=500),
    doc_type: str | None = None,
    language: str | None = None,
    session: Session = Depends(get_session),
) -> list[Document]:
    query = select(Document).order_by(desc(Document.crawl_time)).limit(limit)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    if language:
        query = query.where(Document.language == language)
    return list(session.scalars(query))


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, session: Session = Depends(get_session)) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/exports/latest")
def export_latest(
    limit: int = Query(default=1000, le=5000),
    session: Session = Depends(get_session),
) -> FileResponse:
    path = export_documents_jsonl(session, limit=limit)
    return FileResponse(path=str(path), filename=path.name, media_type="application/json")
