from __future__ import annotations

import re
import unicodedata
from collections import Counter
from urllib.parse import urlparse

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
    r"|last modified\s*:?.*"
    r"|source\s*:?.*"
    r"|doi\s*:?.*"
    r"|\u65e5\u671f\s*:?.*"
    r"|\u66f4\u65b0\u65f6\u95f4\s*:?.*"
    r"|\u4fee\u6539\u65f6\u95f4\s*:?.*"
    r"|\u53d1\u5e03\u65f6\u95f4\s*:?.*"
    r"|\u53d1\u5e03\u65e5\u671f\s*:?.*"
    r"|\u6765\u6e90\s*:?.*"
    r"|\u4f5c\u8005\s*:?.*"
    r"|\u7f16\u8f91\s*:?.*"
    r"|\u8d23\u4efb\u7f16\u8f91\s*:?.*"
    r"|\u680f\u76ee\s*:?.*"
    r"|\u94fe\u63a5\u672c\u6587\s*:?.*"
    r")$",
    re.IGNORECASE,
)
METADATA_LABEL_RE = re.compile(
    r"(\u6765\u6e90|\u65e5\u671f|\u53d1\u5e03\u65f6\u95f4|\u53d1\u5e03\u65e5\u671f|\u4f5c\u8005|"
    r"\u7f16\u8f91|\u8d23\u4efb\u7f16\u8f91|\u680f\u76ee|\u5b57\u53f7|\u6253\u5370\u672c\u9875|"
    r"\u5173\u95ed\u7a97\u53e3|\u94fe\u63a5\u672c\u6587|doi|last modified|updated)",
    re.IGNORECASE,
)
ATTACHMENT_LINE_RE = re.compile(
    r"^(?:\u9644\u4ef6(?:\u4e0b\u8f7d)?|\u4e0b\u8f7d|\u76f8\u5173\u9644\u4ef6|"
    r"\u9644\u4ef61?[\u3001:\uff1a].*|attachment(?:s)?\s*:?.*)$",
    re.IGNORECASE,
)
MARA_SHIPIN_NOISE_LINE_RE = re.compile(
    r"^(?:English|\u65e0\u969c\u788d|\u519c\u4e1a\u519c\u6751\u90e8\u90ae\u7bb1|"
    r"\u4e2d\u56fd\u519c\u4e1a\u519c\u6751\u4fe1\u606f\u7f51|\u653f\u52a1\u670d\u52a1|"
    r"\u4e1a\u52a1\u7ba1\u7406|\u5f53\u524d\u4f4d\u7f6e[:\uff1a]?|>\s*\S+|"
    r"\u60a8\u4f7f\u7528\u7684\u6d4f\u89c8\u5668\u4e0d\u652f\u6301.*javascript.*|"
    r"\[video:.*\]|\u63d0\u793a\u4fe1\u606f|\u60a8\u5373\u5c06\u79bb\u5f00.*|"
    r"\u786e\s*\u5b9a|\u53d6\s*\u6d88|\u65e5\u671f[:\uff1a]?|\u6765\u6e90[:\uff1a]?)$",
    re.IGNORECASE,
)
MARA_SHIPIN_NOISE_TOKEN_RE = re.compile(
    r"(?:English|\u65e0\u969c\u788d|\u519c\u4e1a\u519c\u6751\u90e8\u90ae\u7bb1|"
    r"\u4e2d\u56fd\u519c\u4e1a\u519c\u6751\u4fe1\u606f\u7f51|\u653f\u52a1\u670d\u52a1|"
    r"\u4e1a\u52a1\u7ba1\u7406|\u5f53\u524d\u4f4d\u7f6e|\u63d0\u793a\u4fe1\u606f|"
    r"javascript|\[video:|\u786e\s*\u5b9a|\u53d6\s*\u6d88)",
    re.IGNORECASE,
)
MARA_BREADCRUMB_LINE_RE = re.compile(
    r"^(?:当前位置[:：]?\s*.*|首页\s*[>/＞]\s*.*|新闻\s*[>/＞]\s*.*|"
    r"(?:部门动态|政务动态|工作动态|行业动态|新闻资讯|图片新闻|视频)\s*(?:[>/＞].*)?)$",
    re.IGNORECASE,
)
MARA_BREADCRUMB_TOKEN_RE = re.compile(
    r"(?:当前位置|部门动态|政务动态|工作动态|行业动态|新闻资讯|图片新闻|面包屑)",
    re.IGNORECASE,
)

AGFUNDER_FEED_PATH_RE = re.compile(r"(^/feed/?$)|(/feed/?)$", re.IGNORECASE)
AGFUNDER_HOME_TITLE_RE = re.compile(r"^(home|homepage|agfunder news)$", re.IGNORECASE)
MARA_NOISE_PATH_RE = re.compile(
    r"^/xw/shipin(?:/|$)"
    r"|^/xw/tpxw(?:\d{8})?(?:/|$)"
    r"|^/nybgb/\d{4}/\d{6}/?$",
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
    if ATTACHMENT_LINE_RE.match(normalized):
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


def _clean_mara_shipin_text(text: str) -> tuple[str, int]:
    lines: list[str] = []
    removed = 0
    for raw_line in text.splitlines():
        line = _normalize_line(raw_line)
        if not line:
            continue
        if MARA_SHIPIN_NOISE_LINE_RE.match(line):
            removed += 1
            continue
        if MARA_SHIPIN_NOISE_TOKEN_RE.search(line) and len(line) <= 80:
            removed += 1
            continue
        lines.append(line)
    return "\n".join(lines).strip(), removed


def _clean_mara_general_text(text: str) -> tuple[str, int]:
    lines: list[str] = []
    removed = 0
    for raw_line in text.splitlines():
        line = _normalize_line(raw_line)
        if not line:
            continue
        if "当前位置" in line and len(line) <= 160 and any(marker in line for marker in (">", "＞", "›", "首页", "新闻", "动态")):
            removed += 1
            continue
        if MARA_BREADCRUMB_LINE_RE.match(line):
            removed += 1
            continue
        if line.startswith("当前位置") and len(line) <= 120:
            removed += 1
            continue
        if (" > " in line or "＞" in line or "›" in line) and len(line) <= 120:
            token_hits = len(MARA_BREADCRUMB_TOKEN_RE.findall(line))
            if token_hits >= 1:
                removed += 1
                continue
        lines.append(line)
    return "\n".join(lines).strip(), removed


def _filter_source_keywords(keywords: list[str], source_slug: str) -> list[str]:
    if source_slug != "cn_mara_news":
        return keywords
    filtered: list[str] = []
    for keyword in keywords:
        normalized = _normalize_line(keyword)
        if not normalized:
            continue
        if MARA_BREADCRUMB_TOKEN_RE.search(normalized):
            continue
        if normalized in {"新闻", "首页", "当前位置"}:
            continue
        filtered.append(keyword)
    return filtered


def _clean_source_summary(summary: str, source_slug: str) -> str:
    if source_slug != "cn_mara_news":
        return summary
    cleaned = summary.strip()
    cleaned = re.sub(
        r"^(?:当前位置[:：]?\s*.*?(?:\s+|[>＞›/]+)|"
        r"(?:首页|新闻|部门动态|政务动态|工作动态)\s*[>＞›/]+\s*)+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    if MARA_BREADCRUMB_TOKEN_RE.search(cleaned) and len(cleaned) <= 80:
        return ""
    return cleaned


def _strip_leading_title(title: str, content_text: str) -> str:
    lines = [line for line in content_text.splitlines()]
    while lines and _normalize_line(lines[0]) == _normalize_line(title):
        lines.pop(0)
    return "\n".join(lines).strip()


def _strip_leading_metadata_lines(content_text: str) -> str:
    lines = [line for line in content_text.splitlines()]
    removed = 0
    while lines and removed < 4:
        first = _normalize_line(lines[0])
        label_hits = METADATA_LABEL_RE.findall(first)
        if LEADING_METADATA_RE.match(first) or (
            len(label_hits) >= 2 and len(first) <= 140 and not re.search(r"[。！？!?]$", first)
        ):
            lines.pop(0)
            removed += 1
            continue
        break
    return "\n".join(lines).strip()


def _detect_parse_status(
    title: str,
    content_text: str,
    metadata: dict | None = None,
    source_slug: str | None = None,
    url: str | None = None,
) -> tuple[str, str | None]:
    normalized = re.sub(r"\s+", " ", content_text).strip()
    line_count = len([line for line in content_text.splitlines() if line.strip()])
    metadata = metadata or {}
    url_path = urlparse(url or "").path.lower()
    source_slug = (source_slug or "").lower()

    if source_slug == "agfundernews_global":
        if AGFUNDER_FEED_PATH_RE.search(url_path):
            return "needs_review", "agfunder_feed_or_aggregate"
        if not url_path or url_path == "/" or AGFUNDER_HOME_TITLE_RE.match(title.strip()):
            return "needs_review", "agfunder_homepage"

    if source_slug == "cn_mara_news":
        if MARA_NOISE_PATH_RE.search(url_path):
            return "needs_review", "mara_directory_or_channel_page"
        if len(normalized) < 220 and line_count <= 3:
            return "needs_review", "mara_sparse_page"

    if len(normalized) < 80:
        return "needs_review", "content_too_short"
    if line_count <= 2 and len(normalized) < 160:
        return "needs_review", "content_structure_too_sparse"
    if title.lower() in {"untitled", "untitled pdf"}:
        return "needs_review", "title_missing"
    if source_slug == "cn_mara_news":
        removed_noise_lines = int(metadata.get("mara_removed_noise_lines", 0) or 0)
        residual_noise_hits = int(metadata.get("mara_residual_noise_hits", 0) or 0)
        if "/shipin/" in (url or ""):
            if removed_noise_lines >= 6 and len(normalized) < 260:
                return "needs_review", "mara_shipin_high_noise"
            if residual_noise_hits >= 2:
                return "needs_review", "mara_shipin_residual_noise"
            if line_count <= 2 and len(normalized) < 120:
                return "needs_review", "mara_shipin_metadata_only"
    return "ok", None


def process_document(parsed: ParsedDocument, source: Source) -> ProcessedDocument:
    metadata = dict(parsed.metadata or {})
    content_text = _clean_content_text(parsed.content_text)
    title = _normalize_line(parsed.title) or "Untitled"
    content_text = _strip_leading_title(title, content_text)
    content_text = _strip_leading_metadata_lines(content_text)
    content_text = _strip_leading_title(title, content_text)
    if source.slug == "cn_mara_news":
        content_text, removed_general_noise_lines = _clean_mara_general_text(content_text)
        metadata["mara_removed_general_noise_lines"] = removed_general_noise_lines
    if source.slug == "cn_mara_news" and "/shipin/" in (parsed.url or ""):
        content_text, removed_noise_lines = _clean_mara_shipin_text(content_text)
        content_text = _strip_leading_title(title, content_text)
        content_text = _strip_leading_metadata_lines(content_text)
        metadata["mara_removed_noise_lines"] = removed_noise_lines
        metadata["mara_residual_noise_hits"] = len(MARA_SHIPIN_NOISE_TOKEN_RE.findall(content_text))
    author_org = _normalize_line(parsed.author_org) if parsed.author_org else None
    language = _normalize_language_code(parsed.language) or infer_language(content_text or parsed.title, source.language)
    summary_source = parsed.summary or content_text or parsed.title
    summary = _clean_source_summary(build_summary(summary_source), source.slug)
    keywords = _filter_source_keywords(
        _merge_keyword_lists(
        extract_keywords(content_text, limit=6),
        extract_keywords(title, limit=3),
        limit=8,
        ),
        source.slug,
    )
    content_hash = sha256_text(_normalize_for_hash(content_text))

    parse_status, parse_warning = _detect_parse_status(
        title,
        content_text,
        metadata=metadata,
        source_slug=source.slug,
        url=parsed.url,
    )
    metadata["content_length"] = len(content_text)
    metadata["line_count"] = len([line for line in content_text.splitlines() if line.strip()])
    metadata["parse_status"] = parse_status
    if source.slug == "cn_mara_news" and "/shipin/" in (parsed.url or ""):
        metadata["mara_shipin_page"] = True
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
