# TDS Automation Agent

An LLM-powered automation agent (Tools in Data Science, Project 1) that executes
natural-language tasks against a `/data` directory.

## How it works

1. `POST /run?task=...` — the task is translated (if needed) and planned by an
   LLM (`gpt-4o-mini` via the AI Proxy) into a list of operations.
2. A dispatcher executes each operation via a dedicated handler in `operations/`.
3. `GET /read?path=...` reads a file under `/data` (path-traversal protected).
4. `GET /filter_csv?path=&column=&value=` filters a CSV under `/data`.

Supported operations: `format_file`, `count_dates`, `sort_contacts`,
`extract_logs`, `index_docs`, `extract_email`, `extract_credit_card`,
`find_similar_comments`, `query_tickets`, `fetch_api`, `clone_git`,
`run_sql_query`, `scrape_website`, `resize_image`, `transcribe_audio`,
`md_to_html`.

## Layout

```
app.py            Flask entrypoint (endpoints preserved for evaluation)
core/             config, security (path validation), structured logging
agent/            planner (LLM) + dispatcher
operations/       one module per task handler
tests/            pytest suite (datagen fixtures, LLM mocked)
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # then set AIPROXY_TOKEN
python datagen.py you@example.com   # generate /data fixtures
python app.py                  # serves on :8000 (HTTPS if cert.pem/key.pem present)
```

## Tests & quality

```bash
pip install -e ".[dev]"
ruff check app.py core agent operations tests
pytest -q
```

## Docker

```bash
docker build -t tds-agent .
docker run -e AIPROXY_TOKEN=... -p 8000:8000 tds-agent
```

> **Security note:** never commit `.env`. The token is loaded from the
> environment at runtime.
