# Current Handoff

Last updated: 2026-06-16

## Handoff status

Bootstrap governance state recorded after user-approved writeback.

## Current startup mode

Project Governor Bootstrap Window.

## Current project goal

Stabilize the local InfoHound MVP before expanding scope.

## User-confirmed direction

- Priority: make the local MVP reliable.
- Main flow to verify: crawl, parse, deduplicate, export.
- Not urgent: UI.
- Not urgent: complex deployment.
- No prior GPT-window history or role prompts to import.
- Use minimal governance first.

## Repository-grounded project summary

InfoHound is a Python backend/data collection MVP for agricultural technology intelligence. It has a configured-source crawler, HTML/PDF fetching and parsing path, SQLite-first storage, API endpoints, and JSONL export.

## Bootstrap progress

Completed:

- Read boot protocol.
- Read context routing.
- Read first-window protocol.
- Checked target governance files.
- Confirmed project intake and project state files were empty before initialization.
- Sampled README and key backend files.
- Received user confirmation of immediate project goal and setup preference.
- Drafted project intake, project state, and current handoff.
- Received user approval for durable writeback.
- Wrote initial governance state to PROJECT_INTAKE.md, PROJECT_STATE.md, and this handoff file.

Not complete:

- Validation command definition.
- Local MVP reliability verification.
- Approved next-step execution routing.

## Current boundary

Do not start implementation, Codex execution, validation loops, or repository edits until the next task is explicitly scoped and routed from this handoff.

## Proposed next step

Prepare a narrow local MVP verification packet with:

- Working directory: repository root.
- Read scope: README, pyproject, .env.example, backend/app, backend/config/sources.yaml.
- Initial mode: observation-first. Do not change project files during the first verification pass.
- Initial commands to verify:
  - create and install the local environment;
  - sync sources;
  - run one or more controlled crawls;
  - export JSONL;
  - start API and check health, document listing, and export endpoints.
- Output required:
  - pass/fail table;
  - observed errors;
  - saved document count;
  - export path and sample quality notes;
  - recommended next code or config changes, if any.

## Open questions for the next step

- Which OS/shell should be treated as the primary local run environment?
- Should initial crawl verification use the fastest stable English source, a Chinese policy source, or both?
- Should the first verification avoid network-heavy full crawl and use one source only?
