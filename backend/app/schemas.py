from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    base_url: str
    category: str
    language: str
    country: str
    crawl_type: str
    is_active: bool


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    title: str
    url: str
    publish_time: datetime | None
    language: str
    doc_type: str
    summary: str
    content_text: str
    author_org: str | None
    country: str | None
    keywords_json: list[str]
    crawl_time: datetime
    status: str


class CrawlRunResponse(BaseModel):
    message: str
    sources_processed: int
    documents_saved: int
