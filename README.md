# DorkHub

A self-hosted, single-user tool for authorized bug bounty recon. It has four
independent modules that share one database:

1. **Program discovery** — find self-hosted bug bounty / disclosure programs
   (not hosted on HackerOne, Bugcrowd, etc.) from public sources, and approve
   the ones you want.
2. **Target store** — only the targets you approve become scannable.
3. **Dork library** — a categorized, prioritized set of dorks stored as YAML
   and imported into the database.
4. **Scan engine** — run selected dorks against approved targets through a
   pluggable search provider, with a **live cost estimate before you run**,
   a coverage matrix, and de-duplicated results.

> Only test targets you are authorized to test. DorkHub refuses to scan
> unapproved targets, searches only through official provider APIs, and never
> visits or interacts with results — reviewing a result is a manual step you do
> within the program's scope.

## Architecture

```
frontend/   React + Vite + TypeScript + Tailwind (live UI, cost counter)
backend/    FastAPI + SQLAlchemy + RQ
  app/discovery   program sources + self-hosted filter + bounty classifier
  app/dorks       YAML library + OR-merge renderer
  app/engines     Serper, DataForSEO (swap via one setting)
  app/scanner     planner, cost estimator, runner, dedup, cache
  app/api         REST API
  app/cli.py      run each module from the command line
```

## Install with the one-step installer (recommended)

The installer sets up the backend, builds the web UI, creates `.env`, and
**prompts for your login password** during install. Requires Python 3.12+ and
Node.js 20+.

### Linux / macOS

```bash
cd dork_test
./install.sh
```

### Windows (PowerShell)

```powershell
cd dork_test
# If scripts are blocked, run once: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\install.ps1
```

Then start the server as the installer prints:

```bash
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` and sign in. Add a provider key to `.env`
(`DORKHUB_SERPER_API_KEY` or DataForSEO credentials) before running real searches.

## Manual quick start (local, SQLite, no Redis)

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env          # then edit keys
python -m app.cli set-password "your-password"   # paste hash into .env
python -m app.cli import-dorks
uvicorn app.main:app --reload

# frontend (dev, separate terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000
```

For a single-process deploy, `npm run build` emits into `backend/static/` and
the backend serves the UI at `/`.

## Production (Docker Compose, Postgres + Redis worker)

```bash
cd frontend && npm install && npm run build   # builds into backend/static
cd .. && cp .env.example .env                 # set keys + password hash
docker compose up --build
# http://localhost:8000
```

## Optional AI layer

AI help is off by default and configured entirely in the **Settings** page — no
code changes, no `.env` edits. It is used only on demand (triage a result,
summarize a policy), never automatically.

- **Important:** a Claude Pro/Max subscription is **not** API access. The Anthropic
  API is billed separately (pay per token). A Pro plan cannot be used as an API key.
- **Free, private, self-hosted option:** run a local model with
  [Ollama](https://ollama.com), then in Settings pick the
  "Local / OpenAI-compatible" provider with base URL `http://localhost:11434/v1`
  and a model you've pulled (e.g. `llama3.1`). No key, no cost, nothing leaves
  your machine.
- **Hosted gateways:** any OpenAI-compatible endpoint works (OpenRouter, Groq,
  Together, Gemini's OpenAI-compatible URL). Enter its `/v1` base URL + key.
- **Anthropic API:** choose the Anthropic provider and enter an API key from
  console.anthropic.com (separate billing from Pro).

The provider key is stored **encrypted** in the database (AES via Fernet, keyed
by `DORKHUB_SECRET_KEY`) and never returned to the browser.

## Search providers & cost

Set the keys you have in `.env`; the UI shows which providers are configured and
their per-1000 price, and the scan page shows the estimated dollar cost live as
you change your selection. Pricing moves often — confirm current rates with each
provider.

| Provider | Model | Rough price / 1k | Notes |
|----------|-------|------------------|-------|
| Serper | prepaid credits | ~$0.30–$1.00 | Google results, cheapest at volume |
| DataForSEO | prepaid deposit | ~$0.60–$2.00 | standard queue cheaper than live |

Cost is kept down by: OR-merging dorks in the same group into one query, a query
cache with a TTL you set, and dork priorities so only the high-value set runs on
every target.

## CLI

```bash
python -m app.cli initdb
python -m app.cli import-dorks
python -m app.cli discover disclose_io --limit 20
python -m app.cli estimate --targets 1 2 --dorks 1 2 3 --engine serper
```

## Tests

```bash
cd backend && source .venv/bin/activate && python -m pytest -q
```

See `PLAN.md` for the full design and roadmap.
