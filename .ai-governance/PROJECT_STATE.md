# Project State

Last updated: 2026-06-16

## Status

Initial RepoMind OS project state. User-approved writeback recorded on 2026-06-16.

## Source classification

- Repository evidence:
  - InfoHound is an internal agricultural technology intelligence collection MVP.
  - The repository includes source configuration, crawler scheduling, HTML/PDF fetching, basic extraction and cleanup, deduplication, SQLite-first storage, API routes, and JSONL export.
  - The Python project requires Python 3.11+ and uses FastAPI, SQLAlchemy, APScheduler, httpx, PyMuPDF, trafilatura, PyYAML, pydantic-settings, and related dependencies.
  - The crawl pipeline contains source-level deadline handling, discovered-link processing, URL/final-URL/processed-URL checks, content-hash checks, processed document persistence, raw artifact persistence, and crawl job status updates.
  - The API surface includes health, sources, source sync, crawl run, document list/detail, and latest export endpoints.
- User-confirmed facts:
  - The urgent objective is to make the local MVP stable.
  - The priority flow is crawling, parsing, deduplication, and export.
  - UI and complex deployment are out of short-term scope.
  - There is no prior AI context or role prompt to import.
  - Minimal governance is preferred.
- Inference:
  - The next work should be verification-oriented before feature expansion.
  - The project should avoid broad architecture changes until the current MVP reliability picture is known.

## Current verified picture

InfoHound is a local-first Python backend/data collection MVP for agricultural technology intelligence.

It is designed to:

1. load configured public sources;
2. discover candidate links;
3. fetch HTML and PDF content;
4. parse and clean extracted content;
5. deduplicate records by URL and content hash;
6. persist structured documents and raw artifacts locally;
7. expose documents and crawl operations through a small API;
8. export documents as JSONL.

## Current objective

Stabilize the local MVP and verify reliability of the main data pipeline before adding UI, complex deployment, or large governance structure.

## Current boundaries

### In scope now

- Local environment setup and repeatable startup.
- Source sync verification.
- Controlled crawl smoke tests.
- Parser output inspection.
- Deduplication behavior checks.
- Export file generation and sample review.
- API smoke checks.
- Documentation of verified commands and known weak points.

### Out of scope now

- UI development.
- Complex deployment or production infrastructure.
- Large role library.
- Major architecture rewrites.
- New AI summarization, embeddings, pgvector, or admin UI unless later approved.
- Treating unverified crawl quality as stable.

## Current role setup

Minimal governance only.

Active/needed roles:

- Project Governor: maintain project state, boundaries, approvals, routing, and writeback decisions.
- Repo Governor: audit repository reality, task boundaries, allowed files, forbidden files, and validation commands.

No additional specialist roles are justified yet. Possible future roles such as Data Quality Reviewer, Crawler Maintainer, Parser Specialist, or API Reviewer should remain uncreated until repeated work demonstrates clear need.

## Current risk areas

- The local MVP may run but has not yet been recorded as stable through a repeatable validation checklist.
- Crawling reliability may vary by source because public websites can change behavior, block requests, or return weak content.
- Parser quality may vary across HTML and PDF sources.
- Deduplication logic exists, but edge cases around redirects, duplicate final URLs, and content-hash duplicates should be tested with small controlled runs.
- Export correctness should be checked against actual stored records.
- API and CLI behavior should be aligned so both support the same local validation story.

## Recommended task order after bootstrap approval

1. Establish local validation commands.
2. Run environment/setup smoke test.
3. Run source sync and inspect active source count.
4. Run a small single-source crawl.
5. Inspect database records and raw artifacts.
6. Verify deduplication with repeated crawl or known duplicate inputs.
7. Run JSONL export and inspect sample records.
8. Check API health, documents listing, and export endpoint.
9. Record verified commands and unresolved issues in handoff.
10. Only after the MVP flow is stable, decide whether code changes, tests, parser tuning, or source adjustments are needed.

## Re-decision triggers

Revisit this state if:

- local startup fails;
- crawl reliability is materially worse than expected;
- parser output is too weak for downstream use;
- deduplication creates false positives or misses obvious duplicates;
- export format does not match user needs;
- a UI or deployment requirement becomes urgent;
- repeated workflow pressure shows a specialist role is needed.
