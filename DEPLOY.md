# Free & easy deploy (frontend + backend together)

You get **one public URL**. The Docker image builds the React app and serves it from Flask with the API on `/api/*` — no separate frontend host and no CORS setup.

## Recommended: [Render](https://render.com) (free tier)

| Step | What to do |
|------|------------|
| 1 | Push this repo to **GitHub**. |
| 2 | Sign up at **render.com** (free account). |
| 3 | **Dashboard → New → Blueprint** (or **Web Service** if you prefer). |
| 4 | Connect your repo. If Blueprint, Render reads **`render.yaml`** automatically. |
| 5 | Add **one secret** when prompted: **`SERPAPI_KEY`** = your key from [serpapi.com](https://serpapi.com/). |
| 6 | Click **Apply** / **Deploy**. First build can take **~5–10 minutes** on the free tier. |

When it’s green, open the URL Render shows (e.g. `https://seo-keyword-analyzer.onrender.com`). Share that link.

### Render shows “No repositories found” (GitHub not connecting)

`render.yaml` only loads **after** Render can read your GitHub repo. Fix the GitHub link first:

1. On the Blueprint page, under **Git providers**, click **Configure account** next to **GitHub** (or open [dashboard.render.com → Account Settings → Git Providers](https://dashboard.render.com)).
2. You should land on GitHub’s **Render** app install page. Choose **either**:
   - **All repositories**, **or**
   - **Only select repositories** → add **`Ruchitas123/seo-agent`**.
3. **Save** / **Install** and return to Render. **Refresh** the Blueprint page — your repo list should appear.
4. If you use **two GitHub accounts**, confirm Render is connected to the same account that **owns** [Ruchitas123/seo-agent](https://github.com/Ruchitas123/seo-agent).

**Workaround (public repo only):** On the same screen, use **Public Git Repository** and paste:

`https://github.com/Ruchitas123/seo-agent`

Then continue. Auto-deploy from pushes may be limited compared to the full GitHub connection; fixing the GitHub app is still better long term.

### Free tier caveats

- The service **spins down** after ~15 minutes idle. The **first visit after sleep** may take **30–60 seconds** while it wakes up.
- SerpAPI still has its **own** free limits; a public link means anyone could use **your** quota.

### Optional: CrewAI on Render

The Docker image uses a **small** `requirements-docker.txt` (no CrewAI) so deploys stay fast and free-friendly. To use CrewAI in production you’d need a custom image that installs full `requirements.txt` and set **`OPENAI_API_KEY`**, and you can unset **`CREW_USE_LEGACY`**.

---

## No credit card — share a public link anyway

Many hosts (Render, Railway, Fly.io, etc.) now ask for a **card** for verification or paid plans. If you want **no payment details at all**, these patterns work with **your app running on your machine** (laptop stays on while others use it):

### Option A — [ngrok](https://ngrok.com/) (simplest)

1. Sign up with **email** (free tier; check [ngrok pricing](https://ngrok.com/pricing) for current limits).
2. Install the CLI, run your app locally: `cd backend && CREW_USE_LEGACY=1 python api.py` (after `npm run build` in `frontend` so `dist/` exists, or use your usual dev setup).
3. Run: `ngrok http 8000`
4. ngrok prints an `https://….ngrok-free.app` URL — **that’s what you share**.

Your PC must stay on and connected; free URLs may change when you restart ngrok unless you use a paid reserved domain.

### Option B — [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) (`cloudflared`)

Free Cloudflare account (often **no card** for basic use). You run a small agent on your machine that exposes localhost through Cloudflare. Good if you already use Cloudflare; setup is a few more steps than ngrok.

### Option C — [localtunnel](https://localtunnel.github.io/www/) (quick test)

```bash
npx localtunnel --port 8000
```

Gives a temporary public URL; fine for demos, less ideal for anything serious.

---

**Why not “free cloud with no card” for 24/7 Docker?**  
Abuse and cost pushed most platforms to require a card even for $0 usage. Tunnels avoid that by **not** hosting the app on their servers (only the connection).

---

## Other hosts (also Docker)

Same **`Dockerfile`** works on **Railway**, **Fly.io**, **Google Cloud Run**, etc.: connect the repo, set **`SERPAPI_KEY`** and **`CREW_USE_LEGACY=1`**, expose **`PORT`**.

---

## Local Docker

```bash
docker build -t seo-agent .
docker run --rm -p 8000:8000 -e SERPAPI_KEY=your_key -e CREW_USE_LEGACY=1 seo-agent
```

Open **http://localhost:8000**
