# 🚀 StockVue — Deploy to Vercel

A complete step-by-step guide to deploy your stock investing app to Vercel in under 5 minutes.

## Prerequisites

- A [Vercel account](https://vercel.com/signup) (free tier works)
- Node.js installed locally (`node --version` to verify)
- Git installed locally (`git --version` to verify)

---

## Step 1: Get the code

**From your machine, download the project:**

```bash
# Option A: Download the ZIP
curl -L -o stockvue.zip https://your-source-url/stockvue.zip

# Option B: Create the files manually
mkdir stockvue
cd stockvue
```

### File structure you need:

```
stockvue/
├── api/
│   └── index.py          # Vercel serverless entry point
├── templates/
│   └── index.html         # Frontend SPA
├── backend.py             # FastAPI app
├── vercel.json            # Vercel configuration
└── requirements.txt       # Python dependencies
```

### File contents:

<details>
<summary><b>1. vercel.json</b> — Click to expand</summary>

```json
{
  "functions": {
    "api/**/*.py": {
      "maxDuration": 30,
      "memory": 512
    }
  },
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index.py" },
    { "src": "/(.*)", "dest": "/templates/$1" }
  ]
}
```
</details>

<details>
<summary><b>2. api/index.py</b> — Vercel entry point</summary>

```python
"""
Vercel serverless entry point
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend import app
```
</details>

<details>
<summary><b>3. requirements.txt</b></summary>

```
fastapi>=0.100.0
yfinance>=0.2.0
jinja2>=3.0.0
```
</details>

---

## Step 2: Deploy via CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy (from inside stockvue/ directory)
cd stockvue
vercel --prod
```

Vercel will detect the Python runtime automatically from `requirements.txt` and the routes from `vercel.json`.

That's it. Your app is live.

---

## Important Notes

### Portfolio Data

The SQLite database (`portfolio.db`) **does not persist** on Vercel's ephemeral filesystem. The frontend already has a **localStorage fallback** — your saved stocks survive page refreshes in your browser. If you clear your browser data, the portfolio resets.

For permanent server-side storage, add a database like:
- [**Vercel KV**](https://vercel.com/docs/storage/vercel-kv) (Redis) — easy, free tier
- [**Turso**](https://turso.tech) — SQLite-compatible, great for this app
- [**Supabase**](https://supabase.com) — full PostgreSQL

### Cold Starts

The first request after idle takes ~2-3 seconds (yfinance import). Subsequent calls are <1s. Upgrading to Vercel Pro eliminates cold start delay.

### Backend-only on Railway (Alternative)

If you want persistent SQLite + no cold starts, deploy the backend separately:

```bash
# Deploy to Railway
railway login
railway init
railway up
```

Then point your Vercel frontend at the Railway backend URL by editing the `api()` function in `templates/index.html` to use the Railway URL as a base path.

---

## Quick Test

Once deployed, check:

```bash
# Test the API
curl https://your-app.vercel.app/api/stock/AAPL

# Test the frontend
open https://your-app.vercel.app
```

### Expected behavior:
1. Landing page appears with "Welcome to StockVue"
2. Type "NVDA" in search bar → autocomplete dropdown
3. Click NVDA → chart loads, news appears, metrics populate
4. Click "Add to Portfolio" → stock saves to sidebar
5. Click a portfolio stock → jumps to its detail view
6. Hover ✕ on portfolio item → removes it

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `500: Function not ready` | Wait 30s for cold start, then retry |
| `404 on routes` | Check `vercel.json` route patterns match your file paths |
| `ModuleNotFoundError: yfinance` | Verify `requirements.txt` has `yfinance>=0.2.0` |
| Portfolio resets | That's expected on Vercel — uses localStorage as fallback |
| Slow first load | Normal cold start (~3s). Pro plan removes this. |
