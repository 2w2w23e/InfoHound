from __future__ import annotations

import unittest
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fitz

from tests._support import DatabaseTestCase

from backend.app.db import session_scope
from backend.app.models import CrawlJob, Document, DocumentRaw, Source
from backend.app.services.pipeline import crawl_source
from backend.app.services.types import DiscoveredLink, FetchResult
from backend.app.services.parser import parse_fetch_result, parse_html


def build_pdf_bytes(title: str, body: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), body)
    document.set_metadata(
        {
            "title": title,
            "creationDate": "D:20260424083000+00'00'",
        }
    )
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


class ParserTests(DatabaseTestCase):
    def test_parse_html_uses_fallback_when_primary_extract_is_too_short(self) -> None:
        html = """
        <html>
          <head>
            <meta property="og:title" content="Greenhouse Robotics Update | Demo Lab" />
            <meta property="article:published_time" content="2026-04-20T08:30:00Z" />
            <meta name="author" content="Demo Lab" />
          </head>
          <body>
            <nav>Home</nav>
            <main class="article-content">
              <p>Greenhouse robotics are reducing repetitive field labor in tomato production systems.</p>
              <p>Field trial data showed measurable yield gains and lower pesticide exposure for operators.</p>
            </main>
          </body>
        </html>
        """
        fetch_result = FetchResult(
            url="https://example.com/news/robotics",
            final_url="https://example.com/news/robotics",
            content_type="text/html",
            text=html,
        )

        with patch("backend.app.services.parser.trafilatura.extract", return_value="tiny"):
            parsed = parse_html(fetch_result)

        self.assertEqual(parsed.title, "Greenhouse Robotics Update")
        self.assertEqual(parsed.author_org, "Demo Lab")
        self.assertEqual(parsed.publish_time, datetime(2026, 4, 20, 8, 30, tzinfo=timezone.utc))
        self.assertIn("yield gains", parsed.content_text)
        self.assertEqual(parsed.metadata["extraction_method"], "fallback_html")
        self.assertGreater(parsed.metadata["content_length"], 80)

    def test_parse_pdf_extracts_title_page_count_and_text(self) -> None:
        pdf_bytes = build_pdf_bytes(
            "Autonomous Spraying in Orchards",
            "Autonomous spraying in orchards improves precision and reduces waste.\n"
            "The report summarizes field validation across multiple growing regions.",
        )
        fetch_result = FetchResult(
            url="https://example.com/reports/orchards.pdf",
            final_url="https://example.com/reports/orchards.pdf",
            content_type="application/pdf",
            binary=pdf_bytes,
        )

        parsed = parse_fetch_result(fetch_result)

        self.assertEqual(parsed.title, "Autonomous Spraying in Orchards")
        self.assertIn("reduces waste", parsed.content_text)
        self.assertEqual(parsed.metadata["page_count"], 1)
        self.assertEqual(parsed.metadata["extraction_method"], "pymupdf_text")


class PipelineTests(DatabaseTestCase):
    def test_crawl_source_saves_only_new_unique_documents_and_raw_files(self) -> None:
        with session_scope() as session:
            source = Source(
                slug="demo-pipeline",
                name="Demo Pipeline",
                base_url="https://example.com",
                category="research",
                language="en",
                country="US",
                crawl_type="html_list",
                config_json={"source_timeout_seconds": 60},
            )
            session.add(source)
            session.flush()

            session.add(
                Document(
                    source_id=source.id,
                    title="Already Stored",
                    url="https://example.com/news/already-stored",
                    publish_time=None,
                    language="en",
                    doc_type="research",
                    summary="Existing document",
                    content_text="Existing document body with enough length to be kept in the database.",
                    author_org="Demo Pipeline",
                    country="US",
                    keywords_json=["Existing"],
                    content_hash="existing-hash",
                    status="new",
                )
            )
            session.commit()

            discovered = [
                DiscoveredLink(
                    url="https://example.com/news/already-stored",
                    source_url="https://example.com/news",
                ),
                DiscoveredLink(
                    url="https://example.com/news/new-robotics",
                    source_url="https://example.com/news",
                ),
                DiscoveredLink(
                    url="https://example.com/news/duplicate-body",
                    source_url="https://example.com/news",
                ),
            ]

            article_html = """
            <html>
              <head>
                <title>Robotics in Protected Agriculture</title>
                <meta name="article:published_time" content="2026-04-21T09:00:00Z" />
              </head>
              <body>
                <article>
                  <p>Protected agriculture robotics help growers reduce repetitive labor and improve safety.</p>
                  <p>The article includes field deployment details, operating metrics, and adoption barriers.</p>
                </article>
              </body>
            </html>
            """

            def fetch_side_effect(*args, **kwargs) -> FetchResult:
                url = args[1]
                return FetchResult(
                    url=url,
                    final_url=url,
                    content_type="text/html",
                    text=article_html,
                )

            with patch("backend.app.services.pipeline.build_client", return_value=nullcontext(object())), patch(
                "backend.app.services.pipeline.discover_links",
                return_value=discovered,
            ), patch(
                "backend.app.services.pipeline.fetch_url",
                side_effect=fetch_side_effect,
            ):
                saved_count = crawl_source(session, source)

            document_count = session.query(Document).count()
            raw_paths = [
                (raw.raw_html_path, raw.raw_text_path)
                for raw in session.query(DocumentRaw).all()
            ]
            job_payloads = [
                (job.status, job.discovered_count, job.saved_count)
                for job in session.query(CrawlJob).all()
            ]

        self.assertEqual(saved_count, 1)
        self.assertEqual(document_count, 2)
        self.assertEqual(len(raw_paths), 1)
        self.assertEqual(job_payloads, [("success", 3, 1)])

        raw_html_path, raw_text_path = raw_paths[0]
        self.assertIsNotNone(raw_html_path)
        self.assertIsNotNone(raw_text_path)
        self.assertTrue(Path(raw_html_path).exists())
        self.assertTrue(Path(raw_text_path).exists())


if __name__ == "__main__":
    unittest.main()
