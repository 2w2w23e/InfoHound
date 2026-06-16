from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1F]'


def sanitize_filename(name: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(INVALID_FILENAME_CHARS, "_", name).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    return cleaned[:120]


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def extract_to_txt(input_jsonl: Path, output_dir: Path) -> tuple[int, int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    written = 0
    skipped = 0

    with input_jsonl.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            total += 1
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                print(f"[WARN] line {line_no}: invalid JSON, skipped")
                continue

            title = str(doc.get("title") or "").strip()
            content = str(doc.get("content_text") or doc.get("content") or "").strip()
            doc_id = doc.get("id")

            if not title and not content:
                skipped += 1
                print(f"[WARN] line {line_no}: missing title and content, skipped")
                continue

            if not title:
                title = f"untitled_{doc_id}" if doc_id is not None else f"untitled_{line_no}"

            if not content:
                content = ""

            prefix = f"{doc_id}_" if doc_id is not None else ""
            filename = sanitize_filename(prefix + title) + ".txt"
            target = unique_path(output_dir / filename)

            text = f"标题: {title}\n\n内容:\n{content}\n"
            target.write_text(text, encoding="utf-8")
            written += 1

    return total, written, skipped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract each document title and content from a JSONL file into separate txt files."
    )
    parser.add_argument(
        "input_jsonl",
        type=Path,
        help="Path to documents JSONL file, e.g. data/exports/documents_20260424_070712.jsonl",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        default=Path("data/exports/documents_txt"),
        help="Directory to store per-document txt files (default: data/exports/documents_txt)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_jsonl: Path = args.input_jsonl
    output_dir: Path = args.output_dir

    if not input_jsonl.exists() or not input_jsonl.is_file():
        raise SystemExit(f"Input file not found: {input_jsonl}")

    total, written, skipped = extract_to_txt(input_jsonl, output_dir)
    print(
        f"Done. total_records={total}, written_txt={written}, skipped={skipped}, output_dir={output_dir}"
    )


if __name__ == "__main__":
    main()
