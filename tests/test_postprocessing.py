from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tests._support import DatabaseTestCase

from backend.app.db import init_db, session_scope
from backend.app.models import Document, DocumentRaw, Source
from backend.app.core.config import get_settings
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

    def test_cn_mara_summary_and_keywords_strip_breadcrumb_noise(self) -> None:
        source = Source(
            slug="cn_mara_news",
            name="MOA News",
            base_url="https://www.moa.gov.cn",
            category="policy",
            language="zh",
            country="CN",
            crawl_type="html_list",
        )
        parsed = ParsedDocument(
            title="农业农村部召开春耕生产调度会",
            url="https://www.moa.gov.cn/xw/bmdt/202604/t20260424_6483605.htm",
            publish_time=None,
            content_text=(
                "当前位置：首页 > 新闻 > 部门动态\n"
                "部门动态\n"
                "农业农村部召开春耕生产调度会，部署春耕重点工作，强调稳产保供和田间管理。"
            ),
            author_org="农业农村部网站",
            metadata={},
        )

        processed = process_document(parsed, source)

        self.assertNotIn("当前位置", processed.summary)
        self.assertNotIn("部门动态", processed.summary)
        self.assertFalse(any("当前位置" in keyword or "部门动态" in keyword for keyword in processed.keywords))


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

    def test_usda_export_uses_raw_text_publish_time_fallback(self) -> None:
        settings = get_settings()
        raw_dir = settings.raw_storage_dir / "usda_ars_news" / "20260424"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_text_path = raw_dir / "parasite-hijacks-iron-in-honey-bees.txt"
        raw_text_path.write_text(
            "\n".join(
                [
                    "Contact: Kim Kaplan",
                    "BELTSVILLE, MARYLAND, February 18, 2021—An Agricultural Research Service entomologist discovered a new finding.",
                    "Supporting paragraph follows here with enough detail to exceed export thresholds.",
                ]
            ),
            encoding="utf-8",
        )

        with session_scope() as session:
            source = Source(
                slug="usda_ars_news",
                name="USDA ARS News",
                base_url="https://www.ars.usda.gov",
                category="policy",
                language="en",
                country="US",
                crawl_type="rss",
            )
            session.add(source)
            session.flush()

            document = Document(
                source_id=source.id,
                title="Parasite Hijacks Iron in Honey Bees",
                url="https://www.ars.usda.gov/news-events/news/research-news/2021/parasite-hijacks-iron-in-honey-bees/",
                publish_time=None,
                language="en",
                doc_type="policy",
                summary="Honey bee research update with exportable content.",
                content_text=(
                    "Honey bee research update with enough context to satisfy export thresholds and remain useful "
                    "for downstream consumers."
                ),
                author_org="USDA ARS",
                country="US",
                keywords_json=["Honey Bees", "Research"],
                content_hash="usda-fallback-hash",
                status="new",
            )
            session.add(document)
            session.flush()
            session.add(
                DocumentRaw(
                    document_id=document.id,
                    raw_text_path=str(raw_text_path),
                    raw_metadata_json={"parse_status": "ok"},
                )
            )
            session.commit()

        with session_scope() as session:
            output_path = export_documents_jsonl(session, limit=10)
            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["publish_time"], "2021-02-18T00:00:00+00:00")

    def test_usda_export_supports_abbreviated_month_fallback(self) -> None:
        settings = get_settings()
        raw_dir = settings.raw_storage_dir / "usda_ars_news" / "20260424"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_text_path = raw_dir / "scientists-leverage-ai-to-fast-track-methane-mitigation-stra.txt"
        raw_text_path.write_text(
            "\n".join(
                [
                    "Contact: Maribel Alonso",
                    "BUSHLAND, Texas, Jan. 8, 2025 – A new study from USDA's Agricultural Research Service reveals a new result.",
                    "Additional paragraph text is long enough to satisfy export thresholds and mimic the stored raw text format.",
                ]
            ),
            encoding="utf-8",
        )

        with session_scope() as session:
            source = Source(
                slug="usda_ars_news",
                name="USDA ARS News",
                base_url="https://www.ars.usda.gov",
                category="policy",
                language="en",
                country="US",
                crawl_type="rss",
            )
            session.add(source)
            session.flush()

            document = Document(
                source_id=source.id,
                title="Scientists Leverage AI to Fast-Track Methane Mitigation Strategies in Animal Agriculture",
                url="https://www.ars.usda.gov/news-events/news/research-news/2025/scientists-leverage-ai-to-fast-track-methane-mitigation-strategies-in-animal-agriculture/",
                publish_time=None,
                language="en",
                doc_type="policy",
                summary="Animal agriculture research update with exportable content.",
                content_text=(
                    "Animal agriculture research update with enough context to satisfy export thresholds and remain useful "
                    "for downstream consumers."
                ),
                author_org="USDA ARS",
                country="US",
                keywords_json=["Animal Agriculture", "AI"],
                content_hash="usda-fallback-abbrev-hash",
                status="new",
            )
            session.add(document)
            session.flush()
            session.add(
                DocumentRaw(
                    document_id=document.id,
                    raw_text_path=str(raw_text_path),
                    raw_metadata_json={"parse_status": "ok"},
                )
            )
            session.commit()

        with session_scope() as session:
            output_path = export_documents_jsonl(session, limit=10)
            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["publish_time"], "2025-01-08T00:00:00+00:00")

    def test_cn_mara_export_sanitizes_summary_and_keywords(self) -> None:
        with session_scope() as session:
            source = Source(
                slug="cn_mara_news",
                name="MOA News",
                base_url="https://www.moa.gov.cn",
                category="policy",
                language="zh",
                country="CN",
                crawl_type="html_list",
            )
            session.add(source)
            session.flush()

            document = Document(
                source_id=source.id,
                title="农业农村部召开春耕生产调度会",
                url="https://www.moa.gov.cn/xw/bmdt/202604/t20260424_6483605.htm",
                publish_time=datetime(2026, 4, 24, 8, 30, tzinfo=timezone.utc),
                language="zh",
                doc_type="policy",
                summary="当前位置:首页 > 新闻 > 部门动态 我中心发布了最新公告。",
                content_text=(
                    "我中心发布了最新公告，部署春耕重点工作并说明后续安排。"
                    "此次公告围绕项目申报、评审组织、承担机构确定以及后续工作安排展开，"
                    "内容长度足够支持导出和下游消费。"
                    "同时公告明确了评审流程、承担机构职责、项目执行周期和后续联络方式，"
                    "确保文本长度明显超过导出阈值。"
                ),
                author_org="农业农村部网站",
                country="CN",
                keywords_json=["当前位置", "部门动态", "春耕生产"],
                content_hash="cn-mara-export-clean",
                status="new",
            )
            session.add(document)
            session.commit()

        with session_scope() as session:
            output_path = export_documents_jsonl(session, limit=10)
            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["summary"], "我中心发布了最新公告。")
        self.assertEqual(payload["keywords"], ["春耕生产"])


if __name__ == "__main__":
    unittest.main()
