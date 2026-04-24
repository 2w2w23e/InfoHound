from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests._support import DatabaseTestCase

from backend.app.db import session_scope
from backend.app.main import app
from backend.app.models import Document, Source


class ApiSmokeTests(DatabaseTestCase):
    def seed_api_documents(self) -> tuple[int, int]:
        with session_scope() as session:
            source = Source(
                slug="api-demo",
                name="API Demo",
                base_url="https://example.com",
                category="policy",
                language="en",
                country="US",
                crawl_type="html_list",
            )
            session.add(source)
            session.flush()

            english_doc = Document(
                source_id=source.id,
                title="Automation Improves Irrigation",
                url="https://example.com/docs/automation",
                publish_time=datetime(2026, 4, 24, 8, 30, tzinfo=timezone.utc),
                language="en",
                doc_type="policy",
                summary="Automation improves irrigation planning.",
                content_text=(
                    "Automation improves irrigation planning for large farms by combining sensor telemetry, "
                    "weather forecasts, and repeatable field workflows across distributed greenhouse blocks."
                ),
                author_org="API Demo",
                country="US",
                keywords_json=["Automation", "Irrigation"],
                content_hash="api-demo-en",
                status="new",
            )
            latest_nonexportable_doc = Document(
                source_id=source.id,
                title="Short Sensor Brief",
                url="https://example.com/docs/sensors",
                publish_time=datetime(2026, 4, 24, 9, 30, tzinfo=timezone.utc),
                language="zh",
                doc_type="policy",
                summary="Short zh summary",
                content_text="short zh content",
                author_org="API Demo",
                country="CN",
                keywords_json=["sensor", "brief"],
                content_hash="api-demo-zh",
                status="new",
            )
            session.add_all([english_doc, latest_nonexportable_doc])
            session.flush()
            return english_doc.id, latest_nonexportable_doc.id

    def build_client(self) -> TestClient:
        patches = [
            patch("backend.app.main.sync_sources", return_value=[]),
            patch("backend.app.main.start_scheduler"),
            patch("backend.app.main.stop_scheduler"),
        ]
        for mocked in patches:
            mocked.start()
            self.addCleanup(mocked.stop)
        return TestClient(app)

    def test_health_sources_documents_and_export_endpoints(self) -> None:
        english_id, _ = self.seed_api_documents()

        with self.build_client() as client:
            health_response = client.get("/health")
            sources_response = client.get("/sources")
            documents_response = client.get("/documents", params={"limit": 10, "language": "en"})
            detail_response = client.get(f"/documents/{english_id}")
            export_response = client.get("/exports/latest", params={"limit": 10})

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})

        self.assertEqual(sources_response.status_code, 200)
        self.assertEqual(len(sources_response.json()), 1)
        self.assertEqual(sources_response.json()[0]["slug"], "api-demo")

        self.assertEqual(documents_response.status_code, 200)
        documents_payload = documents_response.json()
        self.assertEqual(len(documents_payload), 1)
        self.assertEqual(documents_payload[0]["title"], "Automation Improves Irrigation")
        self.assertEqual(documents_payload[0]["language"], "en")

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], english_id)

        self.assertEqual(export_response.status_code, 200)
        exported_line = export_response.text.strip().splitlines()[0]
        export_payload = json.loads(exported_line)
        self.assertEqual(export_payload["id"], english_id)
        self.assertEqual(export_payload["title"], "Automation Improves Irrigation")

    def test_export_latest_limit_should_not_return_empty_when_older_rows_are_exportable(self) -> None:
        self.seed_api_documents()

        with self.build_client() as client:
            export_response = client.get("/exports/latest", params={"limit": 1})

        self.assertEqual(export_response.status_code, 200)
        self.assertTrue(
            export_response.text.strip(),
            "Expected at least one exportable row, but the endpoint returned an empty file.",
        )


if __name__ == "__main__":
    unittest.main()
