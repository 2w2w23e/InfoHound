from __future__ import annotations

import re
import unicodedata
from collections import Counter

from ftfy import fix_text

from backend.app.models import Source
from backend.app.services.types import ParsedDocument, ProcessedDocument
from backend.app.services.utils import sha256_text


STOPWORDS = {
    "this",
    "that",
    "with",
    "from",
    "into",
    "using",
    "about",
    "their",
    "have",
    "will",
    "cookie",
    "privacy",
    "policy",
    "copyright",
    "rights",
    "reserved",
}

EN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "via",
    "was",
    "were",
    "will",
    "with",
    "about",
    "after",
    "before",
    "over",
    "under",
    "within",
    "without",
    "article",
    "report",
    "news",
    "update",
    "press",
    "release",
}

EN_KEYWORD_NOISE_WORDS = {
    "article",
    "help",
    "helps",
    "improve",
    "improves",
    "news",
    "report",
    "system",
    "systems",
    "update",
    "updated",
    "updates",
    "announce",
    "announces",
    "announced",
    "release",
    "released",
    "company",
    "companies",
    "study",
    "studies",
}

ZH_STOPWORDS = {
    "一个",
    "一些",
    "他们",
    "以及",
    "但是",
    "因为",
    "如果",
    "我们",
    "你们",
    "关于",
    "通过",
    "因此",
    "同时",
    "还有",
    "为了",
    "进行",
    "相关",
    "表示",
    "指出",
    "公司",
    "集团",
    "报道",
    "新闻",
    "公告",
    "报告",
    "项目",
    "来源",
}

CHINESE_SIGNAL_WORDS = {
    "农业",
    "技术",
    "研究",
    "市场",
    "合作",
    "发展",
    "产品",
    "数据",
    "智能",
    "自动化",
    "供应链",
    "创新",
    "设备",
    "种植",
    "食品",
    "作物",
    "政策",
    "专利",
    "科研",
    "企业",
}

EN_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")
CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\ufeff]")
WHITESPACE_RE = re.compile(r"\s+")
PUNCT_SPACING_RE = re.compile(r"\s*([,.;:!?，。！？；、])\s*")
HYPHEN_SPACING_RE = re.compile(r"\s*([-–—])\s*")
SUMMARY_SPLIT_RE = re.compile(r"(?<=[。！？；.!?])\s+|\n+")

NOISE_LINE_RE = re.compile(
    r"^(home|menu|navigation|subscribe|sign in|log in|all rights reserved|copyright|"
    r"cookie|privacy policy|terms of use|share|facebook|twitter|linkedin|wechat|weibo|"
    r"\u8fd4\u56de\u9876\u90e8|\u4e0a\u4e00\u7bc7|\u4e0b\u4e00\u7bc7|\u6253\u5370|"
    r"\u5173\u95ed\u7a97\u53e3|\u514d\u8d23\u58f0\u660e|\u7248\u6743\u6240\u6709|"
    r"\u7f51\u7ad9\u5730\u56fe|\u8054\u7cfb\u6211\u4eec|\u76f8\u5173\u9605\u8bfb)$",
    re.IGNORECASE,
)
LEADING_METADATA_RE = re.compile(
    r"^(?:"
    r"(?:20\d{2}|19\d{2})[-/.]\d{1,2}[-/.]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"
    r"|published\s*:?.*"
    r"|updated\s*:?.*"
    r"|source\s*:?.*"
    r"|\u53d1\u5e03\u65f6\u95f4\s*:?.*"
    r"|\u53d1\u5e03\u65e5\u671f\s*:?.*"
    r"|\u6765\u6e90\s*:?.*"
    r")$",
    re.IGNORECASE,
)


def _normalize_language_code(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("_", "-")
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("en"):
        return "en"
    return None


def _normalize_text(text: str) -> str:
    normalized = fix_text(text or "")
    normalized = unicodedata.normalize("NFKC", normalized)
    normalized = ZERO_WIDTH_RE.sub("", normalized)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _normalize_for_hash(text: str) -> str:
    normalized = _normalize_text(text).casefold()
    normalized = WHITESPACE_RE.sub(" ", normalized)
    normalized = PUNCT_SPACING_RE.sub(r"\1", normalized)
    normalized = HYPHEN_SPACING_RE.sub(r"\1", normalized)
    return normalized.strip()


def _display_keyword(token: str) -> str:
    if not token:
        return token
    if any("\u4e00" <= char <= "\u9fff" for char in token):
        return token
    if " " in token:
        return " ".join(_display_keyword(part) for part in token.split())
    if "-" in token:
        return "-".join(_display_keyword(part) for part in token.split("-"))
    if re.fullmatch(r"[A-Z0-9]{2,6}", token):
        return token
    if re.fullmatch(r"[A-Za-z]+", token):
        return token[:1].upper() + token[1:].lower()
    return token


def infer_language(text: str, fallback: str = "zh") -> str:
    normalized = _normalize_text(text)
    fallback_language = _normalize_language_code(fallback) or "zh"
    if not normalized:
        return fallback_language

    chinese_chars = sum(1 for char in normalized if "\u4e00" <= char <= "\u9fff")
    latin_chars = sum(1 for char in normalized if char.isascii() and char.isalpha())
    english_words = [match.group(0).casefold() for match in EN_WORD_RE.finditer(normalized)]
    chinese_runs = CJK_RUN_RE.findall(normalized)

    if chinese_chars == 0 and latin_chars > 0:
        return "en"
    if latin_chars == 0 and chinese_chars > 0:
        return "zh"

    chinese_score = chinese_chars * 2 + sum(1 for token in chinese_runs if token in CHINESE_SIGNAL_WORDS)
    english_score = latin_chars + len(english_words) * 2 + sum(1 for token in english_words if token in EN_STOPWORDS)

    if len(english_words) >= 4 and english_score >= chinese_score + 2:
        return "en"
    if chinese_chars >= 6 and chinese_score >= english_score + 2:
        return "zh"
    if english_score > chinese_score * 1.2:
        return "en"
    if chinese_score > english_score * 1.2:
        return "zh"
    return fallback_language if fallback_language in {"zh", "en"} else "zh"


def build_summary(text: str, max_chars: int = 240) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    collapsed = WHITESPACE_RE.sub(" ", normalized).strip()
    if len(collapsed) <= max_chars:
        return collapsed

    segments = [segment.strip() for segment in SUMMARY_SPLIT_RE.split(normalized) if segment.strip()]
    summary_parts: list[str] = []
    for segment in segments:
        if len(segment) < 12:
            continue
        next_summary = segment if not summary_parts else f"{' '.join(summary_parts)} {segment}"
        if len(next_summary) > max_chars:
            if summary_parts:
                break
            clipped = segment[:max_chars].rstrip()
            if " " in clipped:
                clipped = clipped.rsplit(" ", 1)[0].rstrip()
            return f"{clipped}..." if clipped else segment[:max_chars].rstrip()
        summary_parts.append(segment)
        if len(next_summary) >= int(max_chars * 0.85):
            break

    summary = " ".join(summary_parts).strip()
    if not summary:
        summary = collapsed[:max_chars]
        if " " in summary:
            summary = summary.rsplit(" ", 1)[0].rstrip()
    summary = summary.rstrip(" ,;:。！？；.!?")
    if len(summary) < len(collapsed):
        summary = f"{summary}..." if summary else collapsed[:max_chars]
    return summary


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    segments = [segment.strip() for segment in SUMMARY_SPLIT_RE.split(normalized) if segment.strip()]
    if not segments:
        segments = [normalized]

    candidates: list[tuple[str, str]] = []
    weighted_segments = segments[:1] + segments[:1] + segments[1:3]
    for segment in weighted_segments:
        english_tokens = []
        english_display = []

        def flush_english_tokens() -> None:
            if not english_tokens:
                return
            for size in (2, 1):
                for start in range(0, len(english_tokens) - size + 1):
                    phrase_tokens = english_tokens[start : start + size]
                    phrase_display_tokens = english_display[start : start + size]
                    canonical_phrase = " ".join(phrase_tokens)
                    display_phrase = " ".join(phrase_display_tokens)
                    candidates.append((canonical_phrase, display_phrase))
            english_tokens.clear()
            english_display.clear()

        for word in EN_WORD_RE.findall(segment):
            canonical_word = word.casefold()
            if (
                canonical_word in EN_STOPWORDS
                or canonical_word in STOPWORDS
                or canonical_word in EN_KEYWORD_NOISE_WORDS
            ):
                flush_english_tokens()
                continue
            if len(canonical_word) < 3 and not re.fullmatch(r"[A-Z0-9]{2,6}", word):
                continue
            english_tokens.append(canonical_word)
            english_display.append(_display_keyword(word))

        flush_english_tokens()

        for run in CJK_RUN_RE.findall(segment):
            if len(run) < 2:
                continue
            max_size = min(4, len(run))
            for size in range(max_size, 1, -1):
                for start in range(0, len(run) - size + 1):
                    token = run[start : start + size]
                    if token in ZH_STOPWORDS or token in STOPWORDS:
                        continue
                    if len(set(token)) == 1:
                        continue
                    candidates.append((token, token))

    counts: Counter[str] = Counter()
    display_map: dict[str, str] = {}
    first_seen: dict[str, int] = {}
    for canonical, display in candidates:
        canonical = canonical.strip()
        display = _display_keyword(display.strip())
        if not canonical or not display:
            continue
        if canonical in EN_STOPWORDS or canonical in ZH_STOPWORDS or canonical in STOPWORDS:
            continue
        if canonical not in first_seen:
            first_seen[canonical] = len(first_seen)
        counts[canonical] += 1
        current = display_map.get(canonical)
        if current is None:
            display_map[canonical] = display
        elif len(display) > len(current) or (
            display.count(" ") > current.count(" ") and display != current
        ):
            display_map[canonical] = display

    ranked = sorted(
        counts.items(),
        key=lambda item: (
            -display_map[item[0]].count(" "),
            -item[1],
            -len(display_map[item[0]]),
            first_seen[item[0]],
        ),
    )

    keywords: list[str] = []
    for canonical, _ in ranked:
        keyword = display_map[canonical].strip()
        if not keyword or keyword in keywords:
            continue
        if any(keyword in existing for existing in keywords):
            continue
        keywords.append(keyword)
        if len(keywords) >= limit:
            break

    return keywords


def _merge_keyword_lists(*keyword_groups: list[str], limit: int = 8) -> list[str]:
    merged: list[str] = []
    merged_terms: set[str] = set()
    for group in keyword_groups:
        for keyword in group:
            if not keyword or keyword in merged:
                continue
            keyword_terms = {
                term.casefold()
                for term in re.split(r"[\s\-]+", keyword)
                if term.strip()
            }
            if keyword_terms and keyword_terms & merged_terms and len(keyword_terms) <= 2:
                continue
            merged.append(keyword)
            merged_terms.update(keyword_terms)
            if len(merged) >= limit:
                return merged
    return merged


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", fix_text(line or "")).strip()


def _is_noise_line(line: str) -> bool:
    normalized = _normalize_line(line)
    if not normalized:
        return True
    if NOISE_LINE_RE.match(normalized):
        return True
    if len(normalized) <= 2:
        return True
    if normalized.count("|") >= 3 or normalized.count("/") >= 4:
        return True
    return False


def _clean_content_text(text: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in fix_text(text or "").splitlines():
        line = _normalize_line(raw_line)
        if _is_noise_line(line):
            continue
        lowered = line.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _strip_leading_title(title: str, content_text: str) -> str:
    lines = [line for line in content_text.splitlines()]
    while lines and _normalize_line(lines[0]) == _normalize_line(title):
        lines.pop(0)
    return "\n".join(lines).strip()


def _strip_leading_metadata_lines(content_text: str) -> str:
    lines = [line for line in content_text.splitlines()]
    removed = 0
    while lines and removed < 2 and LEADING_METADATA_RE.match(_normalize_line(lines[0])):
        lines.pop(0)
        removed += 1
    return "\n".join(lines).strip()


def _detect_parse_status(title: str, content_text: str) -> tuple[str, str | None]:
    normalized = re.sub(r"\s+", " ", content_text).strip()
    line_count = len([line for line in content_text.splitlines() if line.strip()])
    if len(normalized) < 80:
        return "needs_review", "content_too_short"
    if line_count <= 2 and len(normalized) < 160:
        return "needs_review", "content_structure_too_sparse"
    if title.lower() in {"untitled", "untitled pdf"}:
        return "needs_review", "title_missing"
    return "ok", None


def process_document(parsed: ParsedDocument, source: Source) -> ProcessedDocument:
    content_text = _clean_content_text(parsed.content_text)
    title = _normalize_line(parsed.title) or "Untitled"
    content_text = _strip_leading_title(title, content_text)
    content_text = _strip_leading_metadata_lines(content_text)
    content_text = _strip_leading_title(title, content_text)
    author_org = _normalize_line(parsed.author_org) if parsed.author_org else None
    language = _normalize_language_code(parsed.language) or infer_language(content_text or parsed.title, source.language)
    summary_source = parsed.summary or content_text or parsed.title
    summary = build_summary(summary_source)
    keywords = _merge_keyword_lists(
        extract_keywords(content_text, limit=6),
        extract_keywords(title, limit=3),
        limit=8,
    )
    content_hash = sha256_text(_normalize_for_hash(content_text))

    metadata = dict(parsed.metadata or {})
    parse_status, parse_warning = _detect_parse_status(title, content_text)
    metadata["content_length"] = len(content_text)
    metadata["line_count"] = len([line for line in content_text.splitlines() if line.strip()])
    metadata["parse_status"] = parse_status
    if parse_warning and not metadata.get("parse_warning"):
        metadata["parse_warning"] = parse_warning

    return ProcessedDocument(
        title=title,
        url=parsed.url,
        publish_time=parsed.publish_time,
        content_text=content_text,
        author_org=author_org,
        language=language,
        summary=summary,
        keywords=keywords,
        content_hash=content_hash,
        metadata=metadata,
    )
