# Project Intake

Last updated: 2026-06-16

## Intake Source

Confirmed by the user during RepoMind OS bootstrap on 2026-06-16.
No historical GPT windows, Codex reports, existing role prompts, or prior AI handoff summaries were provided for import.

## Project Summary

InfoHound is a Python local-first MVP for agricultural technology intelligence collection.
The repository already contains application code and a README; before this intake, durable governance state files were empty.

## Current Urgent Objective

Stabilize the local MVP and verify the main workflow is reliable:

1. source configuration and sync;
2. link discovery and crawling;
3. HTML and PDF fetching;
4. parsing and cleanup;
5. URL and content-hash deduplication;
6. local storage;
7. API access and JSONL export.

## Current Users

- Primary current user: the project owner.
- Possible later users: internal team trial users.
- Current product posture: not an external product.

## Setup Mode

Minimal governance setup.
Do not design a large role system at bootstrap.
Do not create role files unless the user later explicitly approves them.

## Short-Term Non-Goals

- No admin UI work yet.
- No complex deployment work yet.
- No broad architecture rewrite.
- No large multi-role governance library.

## Priority Boundaries To Preserve

- Data source compliance must be considered before adding or expanding sources.
- Crawl frequency must remain conservative and source-aware.
- Deduplication logic is part of the core MVP reliability boundary.
- HTML and PDF parsing quality must be sampled and verified, not assumed.
- Failed or unreliable sources should be isolated, disabled, or handled explicitly rather than blocking the whole main flow.
- Codex must not perform broad, unfocused source rewrites; implementation tasks should be narrow and evidence-based.

## Missing Or Unverified

- Whether local smoke tests currently pass in the user's environment.
- Whether automated tests exist or are sufficient.
- Source-by-source success rates and failure modes.
- Parsing quality for representative HTML and PDF samples.
- Export schema expectations for future internal users.
