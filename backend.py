"""
StockVue Backend — FastAPI server
Serves stock data via yfinance + portfolio CRUD via SQLite
"""
import os, json, sqlite3, asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import yfinance as yf
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "portfolio.db")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


# ─── Database ───
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            ticker TEXT PRIMARY KEY,
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            notes TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="StockVue API", lifespan=lifespan)


# ─── Pydantic models ───
class PortfolioAdd(BaseModel):
    ticker: str
    notes: str = ""


# ─── Helpers ───
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Stock API ───
@app.get("/api/stock/{ticker}")
async def get_stock(ticker: str):
    """Get current stock quote + fundamentals"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info or info.get("regularMarketPrice") is None:
            # Try to extract some data anyway
            if info.get("currentPrice") is None and info.get("previousClose") is None:
                raise HTTPException(404, f"No data found for {ticker.upper()}")
    except Exception as e:
        raise HTTPException(404, f"Could not fetch data for {ticker.upper()}: {str(e)}")

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
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
        "avgVolume": info.get("averageVolume"),
        "shortRatio": info.get("shortRatio"),
        "beta": info.get("beta"),
        "description": info.get("longBusinessSummary", ""),
        "website": info.get("website"),
    }


@app.get("/api/chart/{ticker}")
async def get_chart(ticker: str, range: str = Query("1mo", description="1d,5d,1mo,3mo,1y,5y,max")):
    """Get OHLCV chart data"""
    valid_ranges = {"1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "1y": "1y", "5y": "5y", "max": "max"}
    period = valid_ranges.get(range, "1mo")

    # Map display range to yfinance interval for best resolution
    interval_map = {
        "1d": "5m",
        "5d": "15m",
        "1mo": "1h",
        "3mo": "1d",
        "1y": "1d",
        "5y": "1wk",
        "max": "1mo",
    }
    interval = interval_map.get(range, "1d")

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
    except Exception as e:
        raise HTTPException(500, f"Chart data error: {str(e)}")

    if df.empty:
        raise HTTPException(404, f"No chart data for {ticker.upper()}")

    # Reset index to get Date as column
    df = df.reset_index()

    # Column name after reset_index varies: 'Date', 'Datetime', or index name string
    date_col = [c for c in df.columns if 'date' in str(c).lower() or 'time' in str(c).lower()]
    date_col = date_col[0] if date_col else df.columns[0]

    candles = []
    for _, row in df.iterrows():
        ts = row[date_col]
        if hasattr(ts, "timestamp"):
            ts = int(ts.timestamp() * 1000)
        else:
            ts = int(pd.Timestamp(ts).timestamp() * 1000)

        candles.append({
            "time": ts,
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
        })

    return {"ticker": ticker.upper(), "range": range, "interval": interval, "candles": candles}


@app.get("/api/news/{ticker}")
async def get_news(ticker: str):
    """Get latest news for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
    except Exception as e:
        raise HTTPException(500, f"News error: {str(e)}")

    articles = []
    for item in news[:15]:
        articles.append({
            "title": item.get("title", ""),
            "publisher": item.get("publisher", ""),
            "link": item.get("link", ""),
            "summary": item.get("summary", ""),
            "time": item.get("providerPublishTime"),
        })
    return {"ticker": ticker.upper(), "articles": articles}


@app.get("/api/search/{query}")
async def search_tickers(query: str):
    """Search for tickers/companies"""
    try:
        result = yf.Search(query)
        quotes = result.quotes or []
        # Also try to get any additional results
        results = []
        seen = set()
        for q in quotes:
            symbol = q.get("symbol", "")
            if symbol and symbol not in seen:
                seen.add(symbol)
                results.append({
                    "ticker": symbol,
                    "name": q.get("shortname", q.get("longname", "")),
                    "exchange": q.get("exchange", ""),
                    "type": q.get("quoteType", ""),
                })
        return {"query": query, "results": results[:10]}
    except Exception as e:
        return {"query": query, "results": [], "error": str(e)}


# ─── Portfolio API ───
@app.get("/api/portfolio")
async def get_portfolio():
    """Get all saved portfolio stocks with live data"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM portfolio ORDER BY added_at DESC").fetchall()
    conn.close()

    portfolio = []
    for row in rows:
        ticker = row["ticker"]
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("currentPrice", info.get("regularMarketPrice", info.get("previousClose")))
            change = info.get("regularMarketChangePercent")
            name = info.get("longName", info.get("shortName", ticker))
        except Exception:
            price = None
            change = None
            name = ticker

        portfolio.append({
            "ticker": ticker,
            "name": name,
            "price": price,
            "changePercent": change,
            "added_at": row["added_at"],
            "notes": row["notes"],
        })
    return {"portfolio": portfolio}


@app.post("/api/portfolio")
async def add_to_portfolio(data: PortfolioAdd):
    """Add a ticker to portfolio"""
    ticker = data.ticker.upper().strip()
    if not ticker:
        raise HTTPException(400, "Ticker required")

    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO portfolio (ticker, notes) VALUES (?, ?)",
            (ticker, data.notes),
        )
        conn.commit()
        return {"status": "added", "ticker": ticker}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")
    finally:
        conn.close()


@app.delete("/api/portfolio/{ticker}")
async def remove_from_portfolio(ticker: str):
    """Remove a ticker from portfolio"""
    ticker = ticker.upper().strip()
    conn = get_db()
    conn.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()
    return {"status": "removed", "ticker": ticker}


# ─── Frontend ───
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path) as f:
            return f.read()
    return "<h1>StockVue</h1><p>Frontend not built yet. Run the build step.</p>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
