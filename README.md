# InfoHound

InfoHound is a fast-start internal data collection system for agricultural technology intelligence. This MVP is optimized for week-one delivery: configure public sources, discover new links, fetch pages and PDFs, parse them into structured records, save them locally, and expose the results through a small API and export flow.

## What is included

- Source configuration in YAML
- Daily crawl scheduler
- HTML and PDF fetching
- Basic content extraction and cleanup
- URL and content-hash deduplication
- SQLite-first storage that can later switch to PostgreSQL
- JSON API and JSONL export

## Quick start

1. Create a virtual environment and install dependencies.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env
```

2. Start the API.

```powershell
uvicorn backend.app.main:app --reload
```

3. Sync configured sources and run a crawl.

```powershell
python -m backend.app.cli sync-sources
python -m backend.app.cli crawl
python -m backend.app.cli export --limit 100
```

4. Open the API docs.

`http://127.0.0.1:8000/docs`

## Suggested first-week workflow

- Day 1: start the app, sync sources, and confirm the database is created.
- Day 2-4: customize `backend/config/sources.yaml` for your highest-value public sources.
- Day 5: improve parser rules for weak pages and PDFs.
- Day 6-7: sample the exported records and add more sources.

## Project layout

```text
backend/
  app/
    api/
    core/
    services/
  config/
data/
```

## Next upgrades after week one

- Switch to PostgreSQL and pgvector
- Add embeddings and semantic retrieval
- Add AI summarization and entity extraction
- Add a small admin UI for source and crawl monitoring

