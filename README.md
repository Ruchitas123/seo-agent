# SEO Agent

AI-assisted **keyword gap analyzer**: compares a target keyword and your article URL against live Google SERP signals (organic results, People Also Ask, related searches, autocomplete) and scraped competitor pages, then surfaces prioritized gaps your content may be missing.

Product context and architecture live in [PRD.md](./PRD.md).

## Repository layout

| Path | Role |
|------|------|
| [backend](./backend/) | Python pipeline (agents, orchestrator), Flask API, optional Streamlit UI, CLI scripts |
| [frontend](./frontend/) | React + Vite dashboard that talks to the API |

## Quick start

1. **Backend** — [backend/README.md](./backend/README.md): create `backend/.env` with `SERPAPI_KEY`, install dependencies, run `python3 api.py` on port **8000**.

2. **Frontend** — [frontend/README.md](./frontend/README.md): `npm install` and `npm run dev` (Vite proxies `/api` to `http://localhost:8000`).

3. Open the dev URL Vite prints (typically `http://localhost:5173`), enter a keyword and article URL, and run an analysis.

## Requirements

- **Node.js** (for the frontend)
- **Python 3** (for the backend)
- **[SerpAPI](https://serpapi.com/)** API key (required for real Google SERP data)
- **OpenAI API key** (or Ollama) for CrewAI orchestration — see [backend/README.md](./backend/README.md); use `CREW_USE_LEGACY=1` to run without an LLM

Optional tooling in the backend includes Streamlit (`dashboard.py`) and standalone report scripts; see the backend README for details.

## Public URL (free, one link for UI + API)

Use [Render](https://render.com) + [`render.yaml`](./render.yaml): one Docker deploy, no split frontend/backend. Steps in [DEPLOY.md](./DEPLOY.md).
