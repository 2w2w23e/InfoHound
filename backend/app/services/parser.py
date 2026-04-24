from __future__ import annotations

import json
import re
from datetime import datetime

import fitz
import trafilatura
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from ftfy import fix_text

from backend.app.services.types import FetchResult, ParsedDocument


PUBLISH_META_KEYS = (
    ("meta", {"property": "article:published_time"}),
    ("meta", {"name": "article:published_time"}),
    ("meta", {"property": "og:published_time"}),
    ("meta", {"name": "og:published_time"}),
    ("meta", {"name": "publishdate"}),
    ("meta", {"name": "pubdate"}),
    ("meta", {"name": "date"}),
    ("meta", {"name": "dc.date"}),
    ("meta", {"name": "dc.date.issued"}),
    ("meta", {"name": "citation_publication_date"}),
    ("meta", {"name": "citation_date"}),
    ("meta", {"itemprop": "datePublished"}),
    ("meta", {"itemprop": "dateCreated"}),
)

TITLE_META_KEYS = (
    ("meta", {"property": "og:title"}),
    ("meta", {"name": "og:title"}),
    ("meta", {"name": "twitter:title"}),
    ("meta", {"name": "title"}),
    ("meta", {"itemprop": "headline"}),
)

AUTHOR_META_KEYS = (
    {"name": "author"},
    {"property": "article:author"},
    {"property": "og:site_name"},
    {"name": "application-name"},
)

CONTENT_HINT_RE = re.compile(
    r"(article|content|main|detail|news|post|entry|body|text|read|story)",
    re.IGNORECASE,
)
NOISE_LINE_RE = re.compile(
    r"^(home|menu|navigation|subscribe|sign in|log in|all rights reserved|copyright|"
    r"cookie|privacy policy|terms of use|share|facebook|twitter|linkedin|wechat|weibo|"
    r"\u8fd4\u56de\u9876\u90e8|\u4e0a\u4e00\u7bc7|\u4e0b\u4e00\u7bc7|\u6253\u5370|"
    r"\u5173\u95ed\u7a97\u53e3|\u514d\u8d23\u58f0\u660e|\u7248\u6743\u6240\u6709|"
    r"\u7f51\u7ad9\u5730\u56fe|\u8054\u7cfb\u6211\u4eec|\u76f8\u5173\u9605\u8bfb)$",
    re.IGNORECASE,
)
DATE_PATTERN_RE = re.compile(
    r"(?P<date>"
    r"(?:20\d{2}|19\d{2})[-/.\u5e74]\s?\d{1,2}[-/.\u6708]\s?\d{1,2}(?:\u65e5)?"
    r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"
    r")"
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    cleaned = fix_text(str(value)).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.replace("\u5e74", "-").replace("\u6708", "-").replace("\u65e5", " ")
    cleaned = cleaned.replace("/", "-").replace(".", "-")

    try:
        return date_parser.parse(cleaned, fuzzy=True)
    except (TypeError, ValueError, OverflowError):
        return None


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", fix_text(text or "")).strip()


def _looks_like_noise_line(line: str) -> bool:
    normalized = _normalize_whitespace(line).strip("|/-_ ")
    if not normalized:
        return True
    if NOISE_LINE_RE.match(normalized):
        return True
    if len(normalized) <= 2:
        return True
    if normalized.count("|") >= 3 or normalized.count("/") >= 4:
        return True
    return False


def _clean_text_lines(text: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = _normalize_whitespace(raw_line)
        if _looks_like_noise_line(line):
            continue
        if line.lower() in seen:
            continue
        seen.add(line.lower())
        lines.append(line)
    return "\n".join(lines).strip()


def _title_score(candidate: str, site_name: str | None) -> int:
    score = 0
    length = len(candidate)
    if 8 <= length <= 140:
        score += 4
    elif 4 <= length <= 180:
        score += 2
    if re.search(r"[\u4e00-\u9fffA-Za-z]{4,}", candidate):
        score += 2
    if site_name and candidate == site_name:
        score -= 5
    if "|" in candidate or " - " in candidate:
        score -= 1
    return score


def _clean_title(candidate: str, site_name: str | None = None) -> str:
    title = _normalize_whitespace(candidate)
    if not title:
        return ""

    parts = re.split(r"\s(?:\||-|_|::|/)\s", title)
    if len(parts) > 1:
        meaningful = [part.strip() for part in parts if 4 <= len(part.strip()) <= 180]
        if meaningful:
            best = max(meaningful, key=len)
            if site_name and best == site_name and len(meaningful) > 1:
                best = max((part for part in meaningful if part != site_name), key=len, default=best)
            title = best

    if site_name:
        title = re.sub(rf"\s*[-|_]\s*{re.escape(site_name)}$", "", title, flags=re.IGNORECASE).strip()
    return title[:300]


def _extract_json_ld_objects(soup: BeautifulSoup) -> list[dict]:
    objects: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        stack = parsed if isinstance(parsed, list) else [parsed]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                objects.append(item)
                graph = item.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
    return objects


def _extract_title(soup: BeautifulSoup) -> str:
    site_name = None
    site_tag = soup.find("meta", attrs={"property": "og:site_name"})
    if site_tag and site_tag.get("content"):
        site_name = _normalize_whitespace(site_tag["content"])

    candidates: list[str] = []
    for tag_name, attrs in TITLE_META_KEYS:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            candidates.append(tag["content"])

    for key in ("h1", "h2"):
        node = soup.find(key)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                candidates.append(text)

    if soup.title and soup.title.string:
        candidates.append(soup.title.string)

    for item in _extract_json_ld_objects(soup):
        for field in ("headline", "name"):
            value = item.get(field)
            if isinstance(value, str):
                candidates.append(value)

    cleaned_candidates = []
    for candidate in candidates:
        cleaned = _clean_title(candidate, site_name)
        if cleaned and cleaned not in cleaned_candidates:
            cleaned_candidates.append(cleaned)

    if not cleaned_candidates:
        return "Untitled"

    return max(cleaned_candidates, key=lambda item: _title_score(item, site_name))


def _extract_publish_time(soup: BeautifulSoup) -> datetime | None:
    for tag_name, attrs in PUBLISH_META_KEYS:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            parsed = _parse_datetime(tag["content"])
            if parsed:
                return parsed

    for item in _extract_json_ld_objects(soup):
        for field in ("datePublished", "dateCreated", "dateModified", "uploadDate"):
            value = item.get(field)
            if isinstance(value, str):
                parsed = _parse_datetime(value)
                if parsed:
                    return parsed

    for time_tag in soup.find_all("time"):
        parsed = _parse_datetime(time_tag.get("datetime") or time_tag.get_text(" ", strip=True))
        if parsed:
            return parsed

    selectors = soup.select(
        "[class*='date'], [class*='time'], [class*='publish'], [id*='date'], [id*='time'], [id*='publish']"
    )
    for node in selectors[:12]:
        parsed = _parse_datetime(node.get_text(" ", strip=True))
        if parsed:
            return parsed

    text = soup.get_text("\n", strip=True)
    for chunk in text.splitlines()[:40]:
        match = DATE_PATTERN_RE.search(chunk)
        if match:
            parsed = _parse_datetime(match.group("date"))
            if parsed:
                return parsed
    return None


def _extract_author_org(soup: BeautifulSoup) -> str | None:
    for attrs in AUTHOR_META_KEYS:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            value = _normalize_whitespace(tag["content"])
            if value and len(value) <= 255:
                return value

    publisher = soup.find(attrs={"itemprop": "publisher"})
    if publisher:
        value = _normalize_whitespace(publisher.get_text(" ", strip=True))
        if value:
            return value[:255]

    return None


def _extract_main_text_fallback(soup: BeautifulSoup) -> str:
    fallback_soup = BeautifulSoup(str(soup), "html.parser")

    for tag in fallback_soup.find_all(
        ["script", "style", "noscript", "svg", "iframe", "form", "nav", "footer", "aside"]
    ):
        tag.decompose()

    candidates = fallback_soup.find_all(["article", "main", "section", "div"])
    best_text = ""
    for node in candidates:
        attrs = " ".join(
            value
            for value in (
                node.get("id", ""),
                " ".join(node.get("class", [])),
            )
            if value
        )
        if not CONTENT_HINT_RE.search(attrs) and node.name in {"section", "div"}:
            continue
        text = _clean_text_lines(node.get_text("\n", strip=True))
        if len(text) > len(best_text):
            best_text = text

    if len(best_text) >= 80:
        return best_text

    body = fallback_soup.body or fallback_soup
    return _clean_text_lines(body.get_text("\n", strip=True))


def _is_low_quality_content(text: str) -> bool:
    normalized = _normalize_whitespace(text)
    if len(normalized) < 80:
        return True
    if normalized.count(" ") < 10 and normalized.count("\n") < 2 and len(normalized) < 140:
        return True
    return False


def parse_html(fetch_result: FetchResult) -> ParsedDocument:
    html = fetch_result.text or ""
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    publish_time = _extract_publish_time(soup)
    author_org = _extract_author_org(soup)

    extracted = trafilatura.extract(
        html,
        include_links=False,
        include_images=False,
        output_format="txt",
    )
    primary_text = _clean_text_lines(extracted) if extracted else ""
    fallback_text = _extract_main_text_fallback(soup)

    use_fallback = False
    content_text = primary_text
    if _is_low_quality_content(primary_text) and len(fallback_text) > len(primary_text):
        content_text = fallback_text
        use_fallback = True
    elif not primary_text:
        content_text = fallback_text
        use_fallback = True

    title = fix_text(title)
    content_text = fix_text(content_text)
    if author_org:
        author_org = fix_text(author_org)

    return ParsedDocument(
        title=title,
        url=fetch_result.final_url,
        publish_time=publish_time,
        content_text=content_text,
        author_org=author_org,
        metadata={
            "content_type": fetch_result.content_type,
            "extraction_method": "fallback_html" if use_fallback else "trafilatura",
            "content_length": len(content_text),
            "parse_warning": "content_too_short" if _is_low_quality_content(content_text) else None,
        },
    )


def _extract_pdf_page_text(page: fitz.Page) -> str:
    text = page.get_text("text").strip()
    if text:
        return text

    blocks = page.get_text("blocks")
    block_text = "\n".join(block[4].strip() for block in blocks if len(block) > 4 and block[4].strip())
    return block_text.strip()


def _extract_pdf_first_page_lines(page: fitz.Page) -> list[tuple[str, float, int]]:
    lines: list[tuple[str, float, int]] = []
    page_dict = page.get_text("dict")
    order = 0
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(span.get("text", "") for span in spans).strip()
            if not text:
                continue
            max_size = max((span.get("size", 0.0) for span in spans), default=0.0)
            lines.append((text, max_size, order))
            order += 1
    return lines


def _looks_like_pdf_title(line: str) -> bool:
    normalized = _normalize_whitespace(line)
    if not normalized:
        return False
    if len(normalized) < 6 or len(normalized) > 220:
        return False
    if DATE_PATTERN_RE.search(normalized):
        return False
    if re.fullmatch(r"(page\s+)?\d+(\s*/\s*\d+)?", normalized, flags=re.IGNORECASE):
        return False
    if normalized.lower().startswith(("doi", "abstract", "keywords", "author")):
        return False
    letters = sum(char.isalpha() for char in normalized)
    return letters >= 4


def _extract_pdf_title(doc: fitz.Document, pages: list[str]) -> str:
    metadata_title = _normalize_whitespace((doc.metadata or {}).get("title", ""))
    if _looks_like_pdf_title(metadata_title) and metadata_title.lower() != "untitled":
        return metadata_title[:300]

    if len(doc) > 0:
        first_page_candidates = [
            item for item in _extract_pdf_first_page_lines(doc[0])[:16] if _looks_like_pdf_title(item[0])
        ]
        if first_page_candidates:
            best_line, _, _ = max(first_page_candidates, key=lambda item: (item[1], -item[2], len(item[0])))
            return _normalize_whitespace(best_line)[:300]

    first_page_lines = [line.strip() for line in pages[0].splitlines() if line.strip()] if pages else []
    candidates = [line for line in first_page_lines[:12] if _looks_like_pdf_title(line)]
    if candidates:
        return candidates[0][:300]

    return "Untitled PDF"


def parse_pdf(fetch_result: FetchResult) -> ParsedDocument:
    binary = fetch_result.binary or b""
    with fitz.open(stream=binary, filetype="pdf") as doc:
        pages = [_extract_pdf_page_text(page) for page in doc]
        title = _extract_pdf_title(doc, pages)
        publish_time = _parse_datetime((doc.metadata or {}).get("creationDate"))
        page_count = len(pages)

    content_text = fix_text("\n\n".join(page for page in pages if page).strip())

    return ParsedDocument(
        title=title,
        url=fetch_result.final_url,
        publish_time=publish_time,
        content_text=content_text,
        author_org=None,
        metadata={
            "content_type": fetch_result.content_type,
            "page_count": page_count,
            "extraction_method": "pymupdf_text",
            "content_length": len(content_text),
            "parse_warning": "content_too_short" if _is_low_quality_content(content_text) else None,
        },
    )


def parse_fetch_result(fetch_result: FetchResult) -> ParsedDocument:
    if fetch_result.binary is not None:
        return parse_pdf(fetch_result)
    return parse_html(fetch_result)
