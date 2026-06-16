# Project State

Last updated: 2026-06-16

## Verified System Overview

InfoHound is a Python-based local-first MVP for agricultural technology intelligence collection.
It implements a pipeline that:

- loads source configurations from YAML;
- discovers links from configured entry points;
- fetches HTML and PDF content;
- parses and cleans extracted content;
- deduplicates by URL and content hash;
- stores results in a SQLite-first database;
- exposes results via FastAPI endpoints and JSONL export.

## Verified Runtime Behavior

- FastAPI app is initialized via `backend/app/main.py`.
- Database is initialized at startup.
- Source configuration is synced on startup.
- A scheduler is started for periodic crawling tasks.
- API router provides endpoints for:
  - health check
  - source listing and sync
  - crawl execution (single or all sources)
  - document listing and retrieval
  - export of latest crawl results

## Core Pipeline Characteristics

- Crawl process is sequential per source.
- Discovery stage produces link candidates.
- Fetch stage retrieves HTML or binary PDF content.
- Parse stage extracts structured text and metadata.
- Process stage normalizes and enriches content.
- Deduplication uses both URL and content_hash uniqueness constraints.
- Documents below a minimum content length threshold are ignored.

## Current Stability Goal

Primary objective: stabilize MVP reliability of the full pipeline.

Focus areas:

1. Ensure crawl pipeline does not fail silently.
2. Ensure parsing produces usable text for representative sources.
3. Ensure deduplication is correct and does not lose valid data.
4. Ensure export produces consistent JSONL output.
5. Ensure source failures are isolated per-source and do not block global runs.

## Current Non-Goals

- No UI development.
- No production deployment or scaling optimization.
- No multi-role governance system expansion.
- No major architecture refactoring.

## Known Risk Areas

- Source reliability varies significantly (some sources are disabled due to access issues).
- Parsing quality for heterogeneous HTML/PDF sources may be inconsistent.
- Crawl failures may be partially silent due to per-item exception handling.
- Deduplication relies on content hash correctness from parsing stage.

## Operating Constraint

Codex-level changes should be scoped and incremental.
Avoid broad refactors without a validated failure case or observed bug.
