# Backend — SEO Keyword Gap Analyzer

Python services and scripts that fetch Google SERP data (via SerpAPI), autocomplete suggestions, competitor page text, and your article, then compute prioritized keyword gaps.

## Prerequisites

- Python 3.10+ recommended
- A [SerpAPI](https://serpapi.com/) API key

## Configuration

Create a `.env` file in **this directory** (`backend/.env`):

```env
SERPAPI_KEY=your_key_here
```

`config.py` loads `.env` automatically. Do not commit real keys; keep `.env` out of version control.

Optional tuning via environment variables (defaults in `config.py`): `SERP_NUM`, `REQUEST_TIMEOUT`, `SLEEP_BETWEEN_SCRAPES`, `TOP_UNI_LIMIT`, `TOP_BI_LIMIT`, `BIGRAM_MIN_COUNT`, `MIN_SCRAPED_WORDS`, `MAX_HEADING_LENGTH`.

## Install

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## REST API (for the React app)

```bash
python3 api.py
```

Server listens on **http://0.0.0.0:8000**.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | JSON body: `{ "keyword": "...", "url": "https://..." }`. Streams Server-Sent Events: progress steps, then final result or error. Comma-separated keywords merge extra gap sets after the primary run. |

## Pipeline (library / CLI)

- **Orchestrated run**: `from orchestrator import run_analysis` or `python3 orchestrator.py "<keyword>" "<url>"`
- **Agents** (under `agents/`): `serp_agent`, `autocomplete_agent`, `intent_agent`, `scraper_agent`, `gap_agent`

## Other entry points

| File | Purpose |
|------|---------|
| `run_analysis.py` | Standalone / legacy analysis flow |
| `dashboard.py` | Streamlit UI (`streamlit run dashboard.py`) |
| `build_keyword_list.py`, `keyword_report.py`, `serp_keyword_report.py` | Keyword list and reporting utilities |

## Project structure (high level)

```
backend/
  agents/           # SERP, autocomplete, intent, scrape, gap logic
  api.py            # Flask + SSE for the React dashboard
  config.py         # Env and constants
  models.py         # Dataclasses (SERP, pages, gaps, full result)
  orchestrator.py   # Wires agents into one pipeline
```

For product goals and signal sources, see the repo root [PRD.md](../PRD.md).
