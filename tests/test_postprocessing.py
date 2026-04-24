from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from tests._support import DatabaseTestCase

from backend.app.db import init_db, session_scope
from backend.app.models import Document, Source
from backend.app.services.exporter import export_documents_jsonl
from backend.app.services.processor import build_summary, extract_keywords, infer_language, process_document
from backend.app.services.types import ParsedDocument


class ProcessorTests(DatabaseTestCase):
    def test_content_hash_normalizes_whitespace_and_case(self) -> None:
        source = Source(
            slug="demo",
            name="Demo Source",
            base_url="https://example.com",
            category="news",
            language="en",
            country="US",
            crawl_type="html_list",
        )
        parsed_a = ParsedDocument(
            title="Precision Agriculture Update",
            url="https://example.com/a",
            publish_time=None,
            content_text="Precision agriculture improves yields.\n\nMore text here.",
            author_org="Example Org",
            metadata={},
        )
        parsed_b = ParsedDocument(
            title="Precision Agriculture Update",
            url="https://example.com/b",
            publish_time=None,
            content_text=" precision   agriculture   improves   yields.  more text here. ",
            author_org="Example Org",
            metadata={},
        )

        processed_a = process_document(parsed_a, source)
        processed_b = process_document(parsed_b, source)

        self.assertEqual(processed_a.content_hash, processed_b.content_hash)

    def test_infer_language_basic_zh_en(self) -> None:
        self.assertEqual(infer_language("This report discusses greenhouse robotics and irrigation."), "en")
        self.assertEqual(infer_language("这份报告讨论了温室机器人和灌溉技术。"), "zh")

    def test_keywords_are_readable(self) -> None:
        english_keywords = extract_keywords(
            "Precision agriculture systems improve irrigation efficiency. Precision agriculture helps farmers.",
            limit=5,
        )
        chinese_keywords = extract_keywords("智能温室农业技术提升作物产量。智能温室应用持续扩大。", limit=5)

        self.assertTrue(english_keywords)
        self.assertTrue(any(keyword.isascii() for keyword in english_keywords))
        self.assertTrue(chinese_keywords)
        self.assertTrue(any(any("\u4e00" <= char <= "\u9fff" for char in keyword) for keyword in chinese_keywords))

    def test_summary_clips_on_sentence_boundary(self) -> None:
        summary = build_summary(
            "This is the first sentence. This is the second sentence with a few more words. This is the third sentence.",
            max_chars=70,
        )
        self.assertTrue(summary.startswith("This is the first sentence."))
        self.assertLessEqual(len(summary), 73)


class ExporterTests(DatabaseTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def test_jsonl_fields_are_stable(self) -> None:
        with session_scope() as session:
            source = Source(
                slug="demo-source",
                name="Demo Source",
                base_url="https://example.com",
                category="news",
                language="en",
                country="US",
                crawl_type="html_list",
            )
            session.add(source)
            session.flush()

            document = Document(
                source_id=source.id,
                title="Precision Agriculture Update",
                url="https://example.com/articles/1",
                publish_time=datetime(2026, 4, 24, 8, 30, tzinfo=timezone.utc),
                language="en",
                doc_type="news",
                summary="Precision agriculture improves irrigation efficiency.",
                content_text=(
                    "Precision agriculture improves irrigation efficiency across field operations and greenhouse "
                    "monitoring, with measurable reductions in waste and better scheduling for growers."
                ),
                author_org="Example Org",
                country="US",
                keywords_json=["Precision Agriculture", "Irrigation Efficiency"],
                content_hash="abc123",
                status="new",
            )
            session.add(document)
            session.commit()

        with session_scope() as session:
            output_path = export_documents_jsonl(session, limit=10)
            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        expected_keys = [
            "id",
            "source_id",
            "source_slug",
            "source",
            "title",
            "url",
            "content_hash",
            "doc_type",
            "language",
            "country",
            "publish_time",
            "crawl_time",
            "summary",
            "keywords",
            "author_org",
            "content_text",
            "status",
        ]

        self.assertEqual(list(payload.keys()), expected_keys)
        self.assertEqual(payload["content_hash"], "abc123")
        self.assertEqual(payload["source_slug"], "demo-source")
        self.assertEqual(payload["keywords"], ["Precision Agriculture", "Irrigation Efficiency"])
        self.assertIsInstance(payload["publish_time"], str)
        self.assertIsInstance(payload["crawl_time"], str)


if __name__ == "__main__":
    unittest.main()
