# Project Intake

Last updated: 2026-06-16

## Project

InfoHound

## Intake status

Initial RepoMind OS bootstrap intake. User-approved writeback recorded on 2026-06-16.

## Source classification

- Repository evidence:
  - The repository README describes InfoHound as a fast-start internal data collection system for agricultural technology intelligence.
  - The MVP scope includes public source configuration, link discovery, HTML/PDF fetching, basic extraction and cleanup, URL/content-hash deduplication, SQLite-first storage, JSON API, and JSONL export.
  - The repository contains Python backend code for the crawl pipeline, API routes, source configuration, scheduler, database models, and export flow.
- User-confirmed facts:
  - The current urgent goal is to stabilize the local MVP.
  - The immediate reliability focus is the main flow: crawling, parsing, deduplication, and export.
  - UI work is not urgent.
  - Complex deployment is not urgent.
  - There is no historical GPT-window conversation, existing role prompt, or prior AI governance context to import.
  - The project previously relied mainly on code and README for state.
  - The desired governance setup is minimal.
- Inference:
  - The project is currently best treated as a local-first backend/data-pipeline MVP rather than a production service or UI product.
  - The first useful governance outcome should be a reliable project state, boundary list, and next-task sequence rather than a large role system.

## Project purpose

InfoHound collects agricultural technology intelligence from configured public sources, processes fetched HTML/PDF content into structured local records, and exposes collected results through API and JSONL export.

## Repository type

Mixed backend/data collection MVP:

- Python backend service
- Scheduled crawler
- Local SQLite storage
- Public-source configuration
- API and export surface

## Current maturity

MVP implementation exists in the repository, but stable local operation has not yet been durably verified in RepoMind OS state.

## Primary users

Internal project users who need fast agricultural technology intelligence collection and review.

## Current urgent objective

Stabilize the local MVP and verify reliability of the main data pipeline before expanding project scope.

Verification focus:

1. source sync
2. crawl/link discovery
3. page/PDF fetching
4. parsing and cleanup
5. URL/content-hash deduplication
6. local storage and raw artifact saving
7. API listing
8. JSONL export

## Current non-goals

- Do not prioritize UI.
- Do not prioritize complex deployment.
- Do not expand into a large role system.
- Do not route Codex or implementation work until bootstrap state and boundaries are approved.

## Existing context import check

No prior GPT conversation, old role prompt, Codex report, or existing AI context is available for import.

## Preferred governance mode

Minimal governance setup:

- Project Governor for project state, boundaries, approvals, and routing.
- Repo Governor for repository reality checks and task-boundary audits.
- No additional specialist roles unless later repository evidence or repeated workflow pressure justifies them.

## Open questions

- Which local validation command set should become the standard MVP reliability gate?
- Which sources should be considered required for the initial stable crawl smoke test?
- What minimum acceptable export quality should count as MVP-stable?
