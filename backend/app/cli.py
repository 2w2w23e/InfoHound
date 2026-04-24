from __future__ import annotations

import argparse

from sqlalchemy import select

from backend.app.db import init_db, session_scope
from backend.app.models import Source
from backend.app.services.exporter import export_documents_jsonl
from backend.app.services.pipeline import crawl_all_sources, crawl_source
from backend.app.services.source_loader import sync_sources


def sync_sources_command() -> None:
    init_db()
    with session_scope() as session:
        sources = sync_sources(session)
        print(f"Synced {len(sources)} sources.")


def crawl_command(source_slug: str | None) -> None:
    init_db()
    with session_scope() as session:
        if source_slug:
            source = session.scalar(select(Source).where(Source.slug == source_slug))
            if source is None:
                raise SystemExit(f"Source '{source_slug}' not found.")
            saved = crawl_source(session, source)
            print(f"Crawled source '{source_slug}', saved {saved} documents.")
            return

        saved = crawl_all_sources(session)
        print(f"Crawled active sources, saved {saved} documents.")


def export_command(limit: int) -> None:
    init_db()
    with session_scope() as session:
        path = export_documents_jsonl(session, limit=limit)
        print(f"Exported documents to {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="InfoHound MVP CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync-sources", help="Load YAML sources into the database")

    crawl_parser = subparsers.add_parser("crawl", help="Run a crawl job")
    crawl_parser.add_argument("--source-slug", help="Only crawl one configured source")

    export_parser = subparsers.add_parser("export", help="Export documents to JSONL")
    export_parser.add_argument("--limit", type=int, default=1000)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "sync-sources":
        sync_sources_command()
    elif args.command == "crawl":
        crawl_command(args.source_slug)
    elif args.command == "export":
        export_command(args.limit)


if __name__ == "__main__":
    main()

