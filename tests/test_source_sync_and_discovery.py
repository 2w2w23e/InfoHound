from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from tests._support import DatabaseTestCase

from backend.app.db import session_scope
from backend.app.models import Source
from backend.app.services.discovery import discover_links
from backend.app.services.source_loader import sync_sources


class SourceSyncTests(DatabaseTestCase):
    def test_sync_sources_merges_defaults_and_overrides(self) -> None:
        config_data = {
            "defaults": {
                "request": {
                    "timeout_seconds": 11,
                    "retries": 2,
                    "retry_backoff_seconds": 1.5,
                    "headers": {"Accept-Language": "en-US", "X-Default": "1"},
                },
                "discovery": {
                    "same_domain_only": True,
                    "max_links": 15,
                    "entry_urls": ["https://example.com/default-feed"],
                    "link_patterns": ["/reports/"],
                    "exclude_patterns": ["/archive/"],
                },
                "crawl": {"source_timeout_seconds": 120},
            },
            "sources": [
                {
                    "slug": "demo-source",
                    "name": "Demo Source",
                    "base_url": "https://example.com",
                    "category": "research",
                    "language": "en",
                    "country": "US",
                    "request": {
                        "timeout_seconds": 7,
                        "headers": {"User-Agent": "InfoHound-Test"},
                    },
                    "discovery": {
                        "entry_urls": ["https://example.com/news"],
                        "link_patterns": ["/news/"],
                        "exclude_patterns": ["/news/archive/"],
                        "max_links": 8,
                    },
                    "crawl": {"source_timeout_seconds": 45},
                    "headers": {"X-Source": "demo"},
                }
            ],
        }

        with session_scope() as session, patch(
            "backend.app.services.source_loader.load_source_config",
            return_value=config_data,
        ):
            synced = sync_sources(session)
            self.assertEqual(len(synced), 1)
            source = session.query(Source).filter(Source.slug == "demo-source").one()
            self.assertEqual(source.slug, "demo-source")
            self.assertEqual(source.category, "research")
            self.assertEqual(source.config_json["entry_urls"], ["https://example.com/news"])
            self.assertEqual(source.config_json["link_patterns"], ["/reports/", "/news/"])
            self.assertEqual(source.config_json["exclude_patterns"], ["/archive/", "/news/archive/"])
            self.assertEqual(source.config_json["max_links"], 8)
            self.assertEqual(source.config_json["source_timeout_seconds"], 45.0)
            self.assertEqual(source.config_json["request_timeout_seconds"], 7.0)
            self.assertEqual(source.config_json["request_retries"], 2)
            self.assertEqual(source.config_json["request_retry_backoff_seconds"], 1.0)
            self.assertEqual(
                source.config_json["request_headers"],
                {
                    "Accept-Language": "en-US",
                    "X-Default": "1",
                    "X-Source": "demo",
                    "User-Agent": "InfoHound-Test",
                },
            )


class DiscoveryTests(DatabaseTestCase):
    def test_discover_links_filters_html_candidates(self) -> None:
        html = """
        <html>
          <body>
            <a href="/news/alpha">Alpha</a>
            <a href="https://example.com/news/beta">Beta</a>
            <a href="https://example.com/news/alpha">Duplicate Alpha</a>
            <a href="https://example.com/news/archive/old">Archive</a>
            <a href="https://other.example/news/gamma">Other Domain</a>
            <a href="mailto:test@example.com">Mail</a>
          </body>
        </html>
        """

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://example.com/news")
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})

        source = Source(
            slug="demo-html",
            name="Demo HTML",
            base_url="https://example.com",
            category="news",
            language="en",
            country="US",
            crawl_type="html_list",
            config_json={
                "entry_urls": ["https://example.com/news"],
                "link_patterns": ["/news/"],
                "exclude_patterns": ["/news/archive/"],
                "same_domain_only": True,
                "max_links": 10,
                "request_timeout_seconds": 5,
            },
        )

        with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            discovered = discover_links(client, source)

        self.assertEqual(
            [item.url for item in discovered],
            [
                "https://example.com/news/alpha",
                "https://example.com/news/beta",
            ],
        )

    def test_discover_links_supports_xml_feeds(self) -> None:
        rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss>
          <channel>
            <item><link>https://example.com/policy/one</link></item>
            <item><link>https://mirror.example/policy/two</link></item>
          </channel>
        </rss>
        """

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=rss, headers={"content-type": "application/rss+xml"})

        source = Source(
            slug="demo-rss",
            name="Demo RSS",
            base_url="https://example.com",
            category="policy",
            language="en",
            country="GLOBAL",
            crawl_type="html_list",
            config_json={
                "entry_urls": ["https://example.com/feed.xml"],
                "link_patterns": ["/policy/"],
                "exclude_patterns": [],
                "same_domain_only": False,
                "max_links": 10,
                "request_timeout_seconds": 5,
            },
        )

        with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            discovered = discover_links(client, source)

        self.assertEqual(
            [item.url for item in discovered],
            [
                "https://example.com/policy/one",
                "https://mirror.example/policy/two",
            ],
        )


if __name__ == "__main__":
    unittest.main()
