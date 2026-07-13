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

## Deployment

The app binds to `HOST`/`PORT` from the environment (defaults `0.0.0.0:8000`)
and serves plain HTTP when `cert.pem`/`key.pem` are absent, so it works behind
any platform's TLS terminator.

### Render (Docker, free tier — easiest)

1. Push this repo to GitHub (done: `saniyanz/tds-p1new`).
2. Go to https://render.com → **New** → **Web Service** → connect the repo.
3. Environment: **Docker**; Branch: `main`.
4. Add environment variable `AIPROXY_TOKEN` (your real token). Optionally set
   `AGENT_TOKEN` to require `?token=` on every request.
5. Deploy. Render gives you a public URL like `https://tds-agent.onrender.com`.
6. Verify: open the URL (landing page) and `https://<url>/healthz`.

> Render's free tier spins down after inactivity; the first request may be slow.

### Other platforms

- **Railway / Fly.io**: also Docker-native; set `AIPROXY_TOKEN` as a secret.
- **PythonAnywhere / Heroku**: use the `Procfile` (`gunicorn wsgi:app`).

### Local / LAN

```bash
pip install -r requirements.txt
python app.py                 # http://localhost:8000  (or LAN IP)
```

## Security

- Never commit `.env` or your token. The token is read from the environment.
- The agent writes only under `/data` and rejects path traversal / deletion.
- To protect a **public** deployment, set `AGENT_TOKEN` (off by default so the
  evaluator can call `/run` without a token). Anyone with the URL can otherwise
  consume your `AIPROXY_TOKEN` quota.
- `cert.pem`/`key.pem` are a self-signed dev cert; for production use the
  platform's managed TLS instead.
