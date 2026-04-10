# Backend — SEO Keyword Gap Analyzer

Python services and scripts that fetch Google SERP data (via SerpAPI), autocomplete suggestions, competitor page text, and your article, then compute prioritized keyword gaps.

The main pipeline is orchestrated with **[CrewAI](https://github.com/crewAIInc/crewAI)** (`crew_orchestrator.py`): a **sequential crew** of specialist agents, each with a **tool** that calls the same deterministic code in `agents/`.

## Prerequisites

- Python 3.10+ recommended (3.12+ tested with CrewAI)
- A [SerpAPI](https://serpapi.com/) API key
- An **LLM API key** for CrewAI (default: OpenAI), unless you use **Ollama** (see below)

## Configuration

Create a `.env` file in **this directory** (`backend/.env`):

```env
SERPAPI_KEY=your_key_here
OPENAI_API_KEY=your_openai_key_here
```

`config.py` loads `.env` automatically. Do not commit real keys; keep `.env` out of version control.

### CrewAI / LLM

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Required for the default model (`gpt-4o-mini`) so agents can plan tool calls. |
| `CREW_LLM_MODEL` | Override model string (any LiteLLM-supported id, e.g. `gpt-4o`). |
| `CREW_LLM_MODEL=ollama/llama3.2` | Use local Ollama; set `OLLAMA_BASE_URL` if not `http://localhost:11434`. |
| `CREW_VERBOSE=1` | Extra CrewAI logging. |
| `CREW_USE_LEGACY=1` | Skip CrewAI and run the old direct Python chain (no LLM; useful without `OPENAI_API_KEY`). |

Optional tuning via environment variables (defaults in `config.py`): `SERP_NUM`, `REQUEST_TIMEOUT`, `SLEEP_BETWEEN_SCRAPES`, `TOP_UNI_LIMIT`, `TOP_BI_LIMIT`, `BIGRAM_MIN_COUNT`, `MIN_SCRAPED_WORDS`, `MAX_HEADING_LENGTH`.

Intent enrichment (`intent_agent.enrich`): `INTENT_MIN_HEADING_OVERLAP` (default `3`) — minimum shared heading/bigram terms (plus target-keyword tokens) to count a competitor as intent-matched. Uses headings only, not full-page keyword frequency, so overlap is less generic.

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

- **Orchestrated run**: `from orchestrator import run_analysis` or `python3 orchestrator.py "<keyword>" "<url>" <geo>`
- **CrewAI layer**: `crew_orchestrator.py`, `crew_tools.py` (tools wrap `agents/*`)
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
  orchestrator.py   # Entry: CrewAI crew by default; legacy if CREW_USE_LEGACY=1
  crew_orchestrator.py
  crew_tools.py
```

For product goals and signal sources, see the repo root [PRD.md](../PRD.md).
