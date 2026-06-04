"""StockVue — Vercel entry point"""
import sys, os, json, sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

# Vercel imports the file to find 'app' - must work without other deps installed
app = FastAPI(title="StockVue API")

# Now import heavy deps (they'll be installed by pip during build)
import yfinance as yf
import pandas as pd
from pydantic import BaseModel

DB_PATH = "/tmp/portfolio.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS portfolio (ticker TEXT PRIMARY KEY, added_at TEXT DEFAULT (datetime('now')), notes TEXT DEFAULT '')")
    conn.commit(); conn.close()

@app.on_event("startup")
async def _startup():
    init_db()

class PortfolioAdd(BaseModel):
    ticker: str
    notes: str = ""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/stock/{ticker}")
async def get_stock(ticker: str):
    try:
        info = yf.Ticker(ticker).info
        if info.get("regularMarketPrice") is None and info.get("currentPrice") is None and info.get("previousClose") is None:
            raise HTTPException(404, f"No data for {ticker.upper()}")
    except Exception as e:
        raise HTTPException(404, str(e))
    return {
        "ticker": ticker.upper(),
        "name": info.get("longName", info.get("shortName", ticker.upper())),
        "price": info.get("currentPrice", info.get("regularMarketPrice", info.get("previousClose"))),
        "previousClose": info.get("previousClose"),
        "open": info.get("regularMarketOpen", info.get("open")),
        "dayHigh": info.get("regularMarketDayHigh", info.get("dayHigh")),
        "dayLow": info.get("regularMarketDayLow", info.get("dayLow")),
        "volume": info.get("regularMarketVolume", info.get("volume")),
        "change": info.get("regularMarketChange"),
        "changePercent": info.get("regularMarketChangePercent"),
        "marketCap": info.get("marketCap"),
        "peRatio": info.get("trailingPE", info.get("forwardPE")),
        "eps": info.get("trailingEps"),
        "dividendYield": info.get("dividendYield"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "exchange": info.get("exchange"),
        "description": info.get("longBusinessSummary", ""),
    }

@app.get("/api/chart/{ticker}")
async def get_chart(ticker: str, range: str = "1mo"):
    from fastapi import Query
    period = {"1d":"1d","5d":"5d","1mo":"1mo","3mo":"3mo","1y":"1y","5y":"5y","max":"max"}.get(range, "1mo")
    interval = {"1d":"5m","5d":"15m","1mo":"1h","3mo":"1d","1y":"1d","5y":"1wk","max":"1mo"}.get(range, "1d")
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if df.empty:
        raise HTTPException(404, f"No chart data for {ticker.upper()}")
    df = df.reset_index()
    dc = [c for c in df.columns if 'date' in str(c).lower() or 'time' in str(c).lower()]
    dc = dc[0] if dc else df.columns[0]
    candles = []
    for _, r in df.iterrows():
        ts = r[dc]
        if hasattr(ts, "timestamp"): ts = int(ts.timestamp() * 1000)
        else: ts = int(pd.Timestamp(ts).timestamp() * 1000)
        candles.append({"time":ts,"open":round(r["Open"],2),"high":round(r["High"],2),
            "low":round(r["Low"],2),"close":round(r["Close"],2),
            "volume":int(r["Volume"]) if pd.notna(r["Volume"]) else 0})
    return {"ticker": ticker.upper(), "range": range, "candles": candles}

@app.get("/api/news/{ticker}")
async def get_news(ticker: str):
    news = yf.Ticker(ticker).news or []
    return {"ticker": ticker.upper(), "articles": [
        {"title":i.get("title",""),"publisher":i.get("publisher",""),
         "link":i.get("link",""),"time":i.get("providerPublishTime")} for i in news[:15]]}

@app.get("/api/search/{query}")
async def search_tickers(query: str):
    try:
        r = yf.Search(query)
        qs = r.quotes or []
        seen, res = set(), []
        for q in qs:
            s = q.get("symbol","")
            if s and s not in seen:
                seen.add(s)
                res.append({"ticker":s,"name":q.get("shortname",q.get("longname","")),"exchange":q.get("exchange",""),"type":q.get("quoteType","")})
        return {"query": query, "results": res[:10]}
    except:
        return {"query": query, "results": []}

@app.get("/api/portfolio")
async def get_portfolio():
    conn = get_db()
    rows = conn.execute("SELECT * FROM portfolio ORDER BY added_at DESC").fetchall()
    conn.close()
    p = []
    for r in rows:
        try:
            i = yf.Ticker(r["ticker"]).info
            p.append({"ticker":r["ticker"],"name":i.get("longName",i.get("shortName",r["ticker"])),
                "price":i.get("currentPrice",i.get("regularMarketPrice",i.get("previousClose"))),
                "changePercent":i.get("regularMarketChangePercent")})
        except:
            p.append({"ticker":r["ticker"],"name":r["ticker"],"price":None,"changePercent":None})
    return {"portfolio": p}

@app.post("/api/portfolio")
async def add_to_portfolio(data: PortfolioAdd):
    t = data.ticker.upper().strip()
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO portfolio (ticker, notes) VALUES (?, ?)", (t, data.notes))
    conn.commit(); conn.close()
    return {"status": "added", "ticker": t}

@app.delete("/api/portfolio/{ticker}")
async def remove_from_portfolio(ticker: str):
    t = ticker.upper().strip()
    conn = get_db()
    conn.execute("DELETE FROM portfolio WHERE ticker = ?", (t,))
    conn.commit(); conn.close()
    return {"status": "removed", "ticker": t}

@app.get("/")
async def serve_frontend():
    p = os.path.join(os.path.dirname(__file__), "..", "index.html")
    if os.path.exists(p):
        with open(p) as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>StockVue</h1>")