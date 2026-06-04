# StockVue — Full-Stack Stock Investing App

> **Architecture:** Python FastAPI backend → HTML/CSS/JS SPA frontend
> **Data:** yfinance (free, no API key) for real stock data
> **Storage:** SQLite for portfolio persistence
> **Charts:** Chart.js with canvas rendering

## Tasks

### Task 1: Project setup + install deps
- Create project structure
- Install: fastapi, uvicorn, yfinance, aiofiles, jinja2
- Verify deps work

### Task 2: Backend — FastAPI server + stock API endpoints
- GET /api/stock/{ticker} — quote, fundamentals, company info
- GET /api/chart/{ticker}?range=1mo — OHLCV candlestick data
- GET /api/news/{ticker} — latest news from yfinance
- GET /api/search/{query} — ticker/company search via yfinance lookup

### Task 3: Backend — Portfolio CRUD
- SQLite database setup
- GET /api/portfolio — list saved stocks
- POST /api/portfolio — add ticker
- DELETE /api/portfolio/{ticker} — remove ticker

### Task 4: Frontend — Dark Terminal Pro layout
- Full HTML page with 3-panel layout (sidebar | main | watchlist)
- Search bar with autocomplete
- Portfolio summary sidebar
- All CSS styling

### Task 5: Frontend — Interactive chart with Chart.js
- Candlestick chart with timeframe switching (1D, 1W, 1M, 3M, 1Y)
- Volume bars below
- Line chart overlay option

### Task 6: Frontend — Stock detail + news + research
- Stock header (price, change, fundamentals)
- Metrics cards (Mkt Cap, P/E, EPS, Dividend)
- News feed panel
- Add to portfolio button

### Task 7: Frontend — Portfolio management
- View saved stocks in sidebar
- Click to load stock detail
- Remove stocks from portfolio
- Persist via API

### Task 8: Integration + polish
- Wire everything together
- Error handling
- Loading states
- Final styling pass