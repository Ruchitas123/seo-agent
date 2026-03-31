# Frontend — SEO Keyword Gap Dashboard

React 19 + Vite single-page app for running analyses against the backend Flask API.

## Prerequisites

- Node.js 18+ recommended
- Backend API running at `http://localhost:8000` (see [../backend/README.md](../backend/README.md))

## Setup

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

Vite serves the app and **proxies** requests under `/api` to `http://localhost:8000` (see `vite.config.js`). The app uses relative URLs like `/api/analyze`, so you normally do not need to set `VITE_*` env vars for local work.

## Production build

```bash
npm run build
npm run preview   # optional: serve the dist/ folder locally
```

For a production deployment, configure your host or reverse proxy so `/api` routes to the same origin as the static files, or point the frontend at your deployed API (you would then adjust the `API` base URL in `src/App.jsx` if it is not same-origin).

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build |
| `npm run lint` | ESLint |
