from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DiscoveredLink:
    url: str
    source_url: str


@dataclass
class FetchResult:
    url: str
    final_url: str
    content_type: str
    text: str | None = None
    binary: bytes | None = None
    status_code: int = 200


@dataclass
class ParsedDocument:
    title: str
    url: str
    publish_time: datetime | None
    content_text: str
    author_org: str | None
    language: str | None = None
    summary: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    title: str
    url: str
    publish_time: datetime | None
    content_text: str
    author_org: str | None
    language: str
    summary: str
    keywords: list[str]
    content_hash: str
    metadata: dict = field(default_factory=dict)

