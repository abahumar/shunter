# Stock Hunter Webapp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a web interface to Stock Hunter using Flask + HTMX + Tailwind CSS + Lightweight Charts, running locally on `localhost:5000`.

**Architecture:** Flask serves HTML partials via HTMX for SPA-like navigation, plus JSON endpoints for chart data. The existing `scanner/` module is called directly — no rewriting. An in-memory cache with TTL avoids repeated Yahoo Finance fetches.

**Tech Stack:** Python Flask, Jinja2, HTMX (CDN), Tailwind CSS (CDN), TradingView Lightweight Charts (CDN)

---

### Task 1: Add Flask dependency and create app skeleton

**Files:**
- Modify: `requirements.txt`
- Create: `app.py`

**Step 1: Add flask to requirements.txt**

Add `flask>=3.0.0` to `requirements.txt`:

```
yfinance>=0.2.31
pandas>=2.0.0
ta>=0.11.0
rich>=13.0.0
requests>=2.28.0
flask>=3.0.0
```

**Step 2: Install dependencies**

Run: `pip3 install -r requirements.txt`

**Step 3: Create `app.py` with minimal Flask app**

```python
#!/usr/bin/env python3
"""
Stock Hunter Web - Bursa Malaysia Scanner Dashboard
Run: python app.py
"""

import time
import math
from datetime import datetime
from flask import Flask, render_template, request, jsonify

from scanner.symbols import get_all_symbols, get_symbol_name, search_symbol, is_shariah, SYMBOLS
from scanner.data_fetcher import fetch_stock_data, fetch_bulk_data
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock
from scanner.portfolio import add_stock, remove_stock, get_portfolio
from scanner.sectors import analyze_sectors, get_sector
from scanner.signal_tracker import get_tracker_stats, get_recent_signals
from scanner.advanced import (
    multi_timeframe_score,
    find_support_resistance,
    detect_volume_spike,
    calculate_position_size,
)

app = Flask(__name__)

# ── In-memory cache ──
_cache = {}
SCAN_TTL = 900      # 15 minutes
STOCK_TTL = 600     # 10 minutes


def _cache_get(key):
    """Get cached value if not expired."""
    entry = _cache.get(key)
    if entry and (time.time() - entry["time"]) < entry["ttl"]:
        return entry["data"]
    return None


def _cache_set(key, data, ttl):
    """Set cache with TTL."""
    _cache[key] = {"data": data, "time": time.time(), "ttl": ttl}


def _is_htmx(request):
    """Check if request is from HTMX (partial) or direct navigation (full page)."""
    return request.headers.get("HX-Request") == "true"


def _render(template, request, **kwargs):
    """Render as partial (HTMX) or full page (direct navigation)."""
    kwargs["now"] = datetime.now()
    if _is_htmx(request):
        return render_template(template, **kwargs)
    return render_template("base.html", content_template=template, **kwargs)


# ── Scan engine (shared by dashboard and scanner page) ──

def _run_scan(shariah=False, force=False):
    """Run full market scan, using cache if available."""
    cache_key = f"scan_{'shariah' if shariah else 'all'}"
    if not force:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    symbols = get_all_symbols(shariah_only=shariah)

    # Fetch without Rich progress bar (we're in web context)
    stock_data = {}
    failed = 0
    for symbol in symbols:
        df = fetch_stock_data(symbol, period="1y")
        if df is not None:
            stock_data[symbol] = df
        else:
            failed += 1
        time.sleep(0.2)

    results = []
    for symbol, df in stock_data.items():
        try:
            df = compute_indicators(df)
            ind = get_latest_indicators(df)
            analysis = analyze_stock(ind)

            mtf_bonus, mtf_desc = multi_timeframe_score(df)
            analysis["net_score"] += mtf_bonus
            analysis["mtf"] = mtf_desc or ""

            analysis["symbol"] = symbol
            analysis["name"] = get_symbol_name(symbol)
            analysis["close"] = ind.get("close", 0)
            analysis["rsi"] = ind.get("rsi", 0)
            analysis["adx"] = ind.get("adx", 0)
            analysis["shariah"] = is_shariah(symbol)
            analysis["sector"] = get_sector(symbol)

            vol_sma = ind.get("volume_sma_20", 0)
            analysis["volume_ratio"] = (
                ind["volume"] / vol_sma if vol_sma and vol_sma > 0 else 0
            )

            spike = detect_volume_spike(df)
            analysis["spike"] = spike

            results.append(analysis)
        except Exception:
            continue

    results.sort(key=lambda x: x["net_score"], reverse=True)

    scan_result = {
        "results": results,
        "total": len(results),
        "failed": failed,
        "time": datetime.now(),
        "stock_data": stock_data,
    }
    _cache_set(cache_key, scan_result, SCAN_TTL)
    return scan_result


# ── Routes ──

@app.route("/")
def dashboard():
    """Dashboard with summary cards."""
    scan = _cache_get("scan_all")
    return _render("dashboard.html", request, scan=scan)


@app.route("/scan")
def scan():
    """Full scan results page."""
    shariah = request.args.get("shariah") == "1"
    force = request.args.get("refresh") == "1"
    scan = _run_scan(shariah=shariah, force=force)
    return _render("scanner.html", request, scan=scan, shariah=shariah)


@app.route("/stock/<symbol>")
def stock_detail(symbol):
    """Detailed stock analysis page."""
    if not symbol.endswith(".KL"):
        symbol += ".KL"

    cache_key = f"stock_{symbol}"
    detail = _cache_get(cache_key)

    if not detail:
        df = fetch_stock_data(symbol, period="1y")
        if df is None:
            return _render("stock_detail.html", request, error=f"No data for {symbol}", symbol=symbol)

        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        analysis = analyze_stock(ind)
        mtf_bonus, mtf_desc = multi_timeframe_score(df)
        analysis["net_score"] += mtf_bonus
        sr = find_support_resistance(df)
        spike = detect_volume_spike(df)
        sizing = calculate_position_size(10000, ind["close"])

        vol_sma = ind.get("volume_sma_20", 0)
        vol_ratio = ind["volume"] / vol_sma if vol_sma and vol_sma > 0 else 0

        detail = {
            "symbol": symbol,
            "name": get_symbol_name(symbol),
            "close": ind["close"],
            "indicators": ind,
            "analysis": analysis,
            "mtf": {"score": mtf_bonus, "desc": mtf_desc},
            "support_resistance": sr,
            "spike": spike,
            "sizing": sizing,
            "sector": get_sector(symbol),
            "shariah": is_shariah(symbol),
            "volume_ratio": vol_ratio,
        }
        _cache_set(cache_key, detail, STOCK_TTL)

    return _render("stock_detail.html", request, detail=detail, symbol=symbol)


@app.route("/sectors")
def sectors():
    """Sector rotation view."""
    scan = _cache_get("scan_all")
    if not scan:
        scan = _run_scan()

    sector_data = analyze_sectors(scan["stock_data"])
    return _render("sectors.html", request, sectors=sector_data, scan=scan)


@app.route("/spikes")
def spikes():
    """Volume spikes page."""
    scan = _cache_get("scan_all")
    if not scan:
        scan = _run_scan()

    spike_list = []
    for r in scan["results"]:
        if r.get("spike"):
            spike_list.append({
                "symbol": r["symbol"],
                "name": r["name"],
                "close": r["close"],
                "spike": r["spike"],
            })
    spike_list.sort(key=lambda x: x["spike"]["volume_ratio"], reverse=True)
    return _render("spikes.html", request, spikes=spike_list)


@app.route("/portfolio")
def portfolio():
    """Portfolio page."""
    stocks = get_portfolio()

    holdings = []
    for stock in stocks:
        symbol = stock["symbol"]
        df = fetch_stock_data(symbol, period="6mo")
        if df is None:
            holdings.append({**stock, "name": get_symbol_name(symbol), "current": None, "pnl": None, "analysis": None})
            continue

        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        analysis = analyze_stock(ind)
        current = ind["close"]
        pnl = ((current - stock["buy_price"]) / stock["buy_price"]) * 100

        holdings.append({
            **stock,
            "name": get_symbol_name(symbol),
            "current": current,
            "pnl": pnl,
            "analysis": analysis,
        })

    return _render("portfolio.html", request, holdings=holdings)


@app.route("/portfolio/add", methods=["POST"])
def portfolio_add():
    """Add stock to portfolio."""
    symbol = request.form.get("symbol", "").upper()
    if not symbol.endswith(".KL"):
        symbol += ".KL"
    price = float(request.form.get("price", 0))
    quantity = int(request.form.get("quantity", 0))

    if symbol in SYMBOLS and price > 0:
        add_stock(symbol, price, quantity)

    # Return updated portfolio
    return portfolio()


@app.route("/portfolio/remove", methods=["POST"])
def portfolio_remove():
    """Remove stock from portfolio."""
    symbol = request.form.get("symbol", "")
    remove_stock(symbol)
    return portfolio()


@app.route("/tracker")
def tracker():
    """Signal tracker page."""
    stats = get_tracker_stats()
    recent = get_recent_signals(20)
    return _render("tracker.html", request, stats=stats, recent=recent)


# ── API endpoints (JSON) ──

@app.route("/api/chart/<symbol>")
def api_chart(symbol):
    """Return OHLCV + indicator data for Lightweight Charts."""
    if not symbol.endswith(".KL"):
        symbol += ".KL"

    df = fetch_stock_data(symbol, period="1y")
    if df is None:
        return jsonify({"error": "No data"}), 404

    df = compute_indicators(df)

    # Remove timezone info for JSON serialization
    df.index = df.index.tz_localize(None) if df.index.tz else df.index

    candles = []
    ema20 = []
    ema50 = []
    ema200 = []
    bb_upper = []
    bb_lower = []
    volume = []
    macd_data = []
    rsi_data = []

    for idx, row in df.iterrows():
        ts = idx.strftime("%Y-%m-%d")

        candles.append({
            "time": ts,
            "open": round(row["Open"], 4),
            "high": round(row["High"], 4),
            "low": round(row["Low"], 4),
            "close": round(row["Close"], 4),
        })

        vol_color = "rgba(38,166,154,0.5)" if row["Close"] >= row["Open"] else "rgba(239,83,80,0.5)"
        volume.append({"time": ts, "value": int(row["Volume"]), "color": vol_color})

        if not math.isnan(row.get("EMA_20", float("nan"))):
            ema20.append({"time": ts, "value": round(row["EMA_20"], 4)})
        if not math.isnan(row.get("EMA_50", float("nan"))):
            ema50.append({"time": ts, "value": round(row["EMA_50"], 4)})
        if not math.isnan(row.get("EMA_200", float("nan"))):
            ema200.append({"time": ts, "value": round(row["EMA_200"], 4)})
        if not math.isnan(row.get("BB_upper", float("nan"))):
            bb_upper.append({"time": ts, "value": round(row["BB_upper"], 4)})
        if not math.isnan(row.get("BB_lower", float("nan"))):
            bb_lower.append({"time": ts, "value": round(row["BB_lower"], 4)})
        if not math.isnan(row.get("MACD_hist", float("nan"))):
            macd_data.append({
                "time": ts,
                "macd": round(row["MACD"], 4) if not math.isnan(row.get("MACD", float("nan"))) else 0,
                "signal": round(row["MACD_signal"], 4) if not math.isnan(row.get("MACD_signal", float("nan"))) else 0,
                "histogram": round(row["MACD_hist"], 4),
            })
        if not math.isnan(row.get("RSI", float("nan"))):
            rsi_data.append({"time": ts, "value": round(row["RSI"], 2)})

    return jsonify({
        "candles": candles,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "volume": volume,
        "macd": macd_data,
        "rsi": rsi_data,
    })


@app.route("/api/search")
def api_search():
    """Search stocks by name or code."""
    q = request.args.get("q", "")
    if len(q) < 1:
        return jsonify([])
    results = search_symbol(q)
    return jsonify([{"symbol": code, "name": name} for code, name in results[:10]])


if __name__ == "__main__":
    print("\n🎯 Stock Hunter Web — http://localhost:5000\n")
    app.run(debug=True, port=5000)
```

**Step 4: Verify Flask starts**

Run: `python3 app.py &` then `curl -s http://localhost:5000 | head -5`
Expected: Flask responds (will be 500 until templates exist, that's OK)
Kill the server after test.

**Step 5: Commit**

```bash
git add requirements.txt app.py
git commit -m "feat: add Flask app skeleton with routes and cache layer"
```

---

### Task 2: Create base template (shell with sidebar + HTMX)

**Files:**
- Create: `templates/base.html`

**Step 1: Create the base HTML shell**

This is the SPA-like shell. Sidebar navigation uses HTMX to swap the `#main-content` div. Includes Tailwind CSS, HTMX, and Lightweight Charts via CDN.

```html
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Hunter</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        surface: { DEFAULT: '#0f172a', 50: '#1e293b', 100: '#334155', 200: '#475569' },
                        accent: '#3b82f6',
                    }
                }
            }
        }
    </script>
    <style>
        body { background: #0f172a; }
        .nav-link { transition: all 0.15s; }
        .nav-link:hover, .nav-link.active { background: #1e293b; border-left: 3px solid #3b82f6; }
        .signal-strong-buy { background: #166534; color: #fff; }
        .signal-buy { color: #22c55e; }
        .signal-watch { color: #eab308; }
        .signal-hold { color: #94a3b8; }
        .signal-sell { color: #ef4444; }
        .signal-strong-sell { background: #991b1b; color: #fff; }
        .htmx-request .loading-spinner { display: block; }
        .htmx-request .content-body { opacity: 0.4; }
        .loading-spinner { display: none; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; }
    </style>
</head>
<body class="text-gray-200 min-h-screen flex">

    <!-- Sidebar -->
    <nav class="w-56 bg-surface-50 border-r border-surface-100 flex flex-col fixed h-full">
        <div class="p-4 border-b border-surface-100">
            <h1 class="text-lg font-bold text-white flex items-center gap-2">
                <span class="text-2xl">🎯</span> Stock Hunter
            </h1>
            <p class="text-xs text-gray-500 mt-1">Bursa Malaysia Scanner</p>
        </div>
        <div class="flex-1 py-4">
            <a href="/" hx-get="/" hx-target="#main-content" hx-push-url="true"
               class="nav-link block px-4 py-2.5 text-sm text-gray-300 hover:text-white" id="nav-dashboard">
                📊 Dashboard
            </a>
            <a href="/scan" hx-get="/scan" hx-target="#main-content" hx-push-url="true"
               class="nav-link block px-4 py-2.5 text-sm text-gray-300 hover:text-white" id="nav-scanner">
                🔍 Scanner
            </a>
            <a href="/sectors" hx-get="/sectors" hx-target="#main-content" hx-push-url="true"
               class="nav-link block px-4 py-2.5 text-sm text-gray-300 hover:text-white" id="nav-sectors">
                🔄 Sectors
            </a>
            <a href="/spikes" hx-get="/spikes" hx-target="#main-content" hx-push-url="true"
               class="nav-link block px-4 py-2.5 text-sm text-gray-300 hover:text-white" id="nav-spikes">
                ⚡ Volume Spikes
            </a>
            <a href="/portfolio" hx-get="/portfolio" hx-target="#main-content" hx-push-url="true"
               class="nav-link block px-4 py-2.5 text-sm text-gray-300 hover:text-white" id="nav-portfolio">
                💼 Portfolio
            </a>
            <a href="/tracker" hx-get="/tracker" hx-target="#main-content" hx-push-url="true"
               class="nav-link block px-4 py-2.5 text-sm text-gray-300 hover:text-white" id="nav-tracker">
                📈 Signal Tracker
            </a>
        </div>
        <div class="p-4 border-t border-surface-100 text-xs text-gray-600">
            Data from Yahoo Finance
        </div>
    </nav>

    <!-- Main Content -->
    <main class="ml-56 flex-1 min-h-screen">
        <div class="p-6">
            <!-- Loading spinner -->
            <div class="loading-spinner flex justify-center py-20">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
            </div>
            <!-- Content -->
            <div id="main-content" class="content-body">
                {% if content_template %}
                    {% include content_template %}
                {% endif %}
            </div>
        </div>
    </main>

    <!-- HTMX nav active state + chart cleanup -->
    <script src="/static/app.js"></script>
</body>
</html>
```

**Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: add base template with sidebar navigation and dark theme"
```

---

### Task 3: Create Dashboard page

**Files:**
- Create: `templates/dashboard.html`

**Step 1: Create dashboard template**

Shows summary cards (BUY/WATCH/SELL counts), top 5 picks, and a prompt to run a scan if no cached data exists.

```html
<div class="space-y-6">
    <div class="flex items-center justify-between">
        <h2 class="text-2xl font-bold text-white">Dashboard</h2>
        <button hx-get="/scan" hx-target="#main-content" hx-push-url="/scan"
                class="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition">
            🔍 Run Scan
        </button>
    </div>

    {% if scan %}
    {% set results = scan.results %}
    {% set buy_count = results|selectattr("signal", "in", ["STRONG BUY", "BUY"])|list|length %}
    {% set watch_count = results|selectattr("signal", "equalto", "WATCH")|list|length %}
    {% set sell_count = results|selectattr("signal", "in", ["SELL", "STRONG SELL"])|list|length %}

    <!-- Summary Cards -->
    <div class="grid grid-cols-4 gap-4">
        <div class="card p-4">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Total Scanned</p>
            <p class="text-3xl font-bold text-white mt-1">{{ scan.total }}</p>
        </div>
        <div class="card p-4">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Buy Signals</p>
            <p class="text-3xl font-bold text-green-400 mt-1">{{ buy_count }}</p>
        </div>
        <div class="card p-4">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Watch</p>
            <p class="text-3xl font-bold text-yellow-400 mt-1">{{ watch_count }}</p>
        </div>
        <div class="card p-4">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Sell Signals</p>
            <p class="text-3xl font-bold text-red-400 mt-1">{{ sell_count }}</p>
        </div>
    </div>

    <!-- Top 5 Picks -->
    <div class="card p-4">
        <h3 class="text-lg font-semibold text-white mb-3">Top 5 Picks</h3>
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-500 text-xs uppercase">
                    <th class="text-left pb-2">#</th>
                    <th class="text-left pb-2">Symbol</th>
                    <th class="text-left pb-2">Name</th>
                    <th class="text-right pb-2">Price</th>
                    <th class="text-center pb-2">Signal</th>
                    <th class="text-right pb-2">Score</th>
                </tr>
            </thead>
            <tbody>
                {% for r in results[:5] %}
                <tr class="border-t border-surface-100 hover:bg-surface-100 cursor-pointer"
                    hx-get="/stock/{{ r.symbol }}" hx-target="#main-content" hx-push-url="true">
                    <td class="py-2 text-gray-500">{{ loop.index }}</td>
                    <td class="py-2 text-accent font-mono">{{ r.symbol }}</td>
                    <td class="py-2">{{ r.name }}</td>
                    <td class="py-2 text-right">{{ "%.2f"|format(r.close) }}</td>
                    <td class="py-2 text-center">
                        <span class="px-2 py-0.5 rounded text-xs font-bold
                            {% if r.signal == 'STRONG BUY' %}signal-strong-buy
                            {% elif r.signal == 'BUY' %}signal-buy
                            {% elif r.signal == 'WATCH' %}signal-watch
                            {% elif r.signal == 'SELL' %}signal-sell
                            {% elif r.signal == 'STRONG SELL' %}signal-strong-sell
                            {% else %}signal-hold{% endif %}">
                            {{ r.signal }}
                        </span>
                    </td>
                    <td class="py-2 text-right font-mono">{{ r.net_score }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Last Scan Info -->
    <p class="text-xs text-gray-600">
        Last scan: {{ scan.time.strftime('%d %b %Y, %I:%M %p') }} &bull;
        {{ scan.total }} stocks analyzed
    </p>

    {% else %}
    <!-- No scan data yet -->
    <div class="card p-12 text-center">
        <p class="text-4xl mb-4">🎯</p>
        <h3 class="text-xl font-semibold text-white mb-2">Welcome to Stock Hunter</h3>
        <p class="text-gray-400 mb-6">Run your first scan to see BUY/SELL signals across Bursa Malaysia</p>
        <button hx-get="/scan" hx-target="#main-content" hx-push-url="/scan"
                class="px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-blue-600 transition">
            🔍 Start Scanning
        </button>
    </div>
    {% endif %}
</div>
```

**Step 2: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: add dashboard page with summary cards and top picks"
```

---

### Task 4: Create Scanner page

**Files:**
- Create: `templates/scanner.html`

**Step 1: Create scanner template**

Full scan results table with signal filtering and refresh button.

```html
<div class="space-y-4">
    <div class="flex items-center justify-between">
        <h2 class="text-2xl font-bold text-white">Scanner</h2>
        <div class="flex items-center gap-3">
            <!-- Shariah toggle -->
            <label class="flex items-center gap-2 text-sm text-gray-400">
                <input type="checkbox" id="shariah-toggle" {% if shariah %}checked{% endif %}
                       class="rounded border-gray-600"
                       hx-get="/scan" hx-target="#main-content" hx-push-url="true"
                       hx-include="this" name="shariah" value="1">
                ☪ Shariah only
            </label>
            <button hx-get="/scan?refresh=1{% if shariah %}&shariah=1{% endif %}"
                    hx-target="#main-content"
                    class="px-4 py-2 bg-surface-100 text-gray-300 rounded-lg text-sm hover:bg-surface-200 transition">
                🔄 Refresh
            </button>
        </div>
    </div>

    {% if scan %}
    {% set results = scan.results %}

    <!-- Filter buttons -->
    <div class="flex gap-2" id="signal-filters">
        <button onclick="filterSignals('all')" class="filter-btn active px-3 py-1 rounded text-xs font-medium bg-surface-100 text-gray-300">
            All ({{ results|length }})
        </button>
        <button onclick="filterSignals('buy')" class="filter-btn px-3 py-1 rounded text-xs font-medium bg-surface-100 text-green-400">
            BUY ({{ results|selectattr("signal", "in", ["STRONG BUY", "BUY"])|list|length }})
        </button>
        <button onclick="filterSignals('watch')" class="filter-btn px-3 py-1 rounded text-xs font-medium bg-surface-100 text-yellow-400">
            WATCH ({{ results|selectattr("signal", "equalto", "WATCH")|list|length }})
        </button>
        <button onclick="filterSignals('sell')" class="filter-btn px-3 py-1 rounded text-xs font-medium bg-surface-100 text-red-400">
            SELL ({{ results|selectattr("signal", "in", ["SELL", "STRONG SELL"])|list|length }})
        </button>
    </div>

    <!-- Search -->
    <div>
        <input type="text" id="stock-search" placeholder="Search by symbol or name..."
               onkeyup="searchTable(this.value)"
               class="w-full md:w-80 px-3 py-2 bg-surface-100 border border-surface-200 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-accent">
    </div>

    <!-- Results Table -->
    <div class="card overflow-hidden">
        <table class="w-full text-sm" id="scan-table">
            <thead>
                <tr class="text-gray-500 text-xs uppercase bg-surface-100">
                    <th class="text-left p-3">#</th>
                    <th class="text-left p-3">Symbol</th>
                    <th class="text-left p-3">Name</th>
                    <th class="text-right p-3">Price (RM)</th>
                    <th class="text-center p-3">Signal</th>
                    <th class="text-right p-3">Score</th>
                    <th class="text-right p-3">RSI</th>
                    <th class="text-right p-3">ADX</th>
                    <th class="text-right p-3">Vol</th>
                    <th class="text-left p-3">Sector</th>
                    <th class="text-left p-3">Key Reasons</th>
                </tr>
            </thead>
            <tbody>
                {% for r in results %}
                <tr class="border-t border-surface-100 hover:bg-surface-100 cursor-pointer stock-row"
                    data-signal="{{ r.signal }}"
                    hx-get="/stock/{{ r.symbol }}" hx-target="#main-content" hx-push-url="true">
                    <td class="p-3 text-gray-500">{{ loop.index }}</td>
                    <td class="p-3 text-accent font-mono">{{ r.symbol }}</td>
                    <td class="p-3">{{ r.name }}</td>
                    <td class="p-3 text-right font-mono">{{ "%.2f"|format(r.close) }}</td>
                    <td class="p-3 text-center">
                        <span class="px-2 py-0.5 rounded text-xs font-bold
                            {% if r.signal == 'STRONG BUY' %}signal-strong-buy
                            {% elif r.signal == 'BUY' %}signal-buy
                            {% elif r.signal == 'WATCH' %}signal-watch
                            {% elif r.signal == 'SELL' %}signal-sell
                            {% elif r.signal == 'STRONG SELL' %}signal-strong-sell
                            {% else %}signal-hold{% endif %}">
                            {{ r.signal }}
                        </span>
                    </td>
                    <td class="p-3 text-right font-mono">{{ r.net_score }}</td>
                    <td class="p-3 text-right font-mono">{{ "%.0f"|format(r.rsi) if r.rsi else "-" }}</td>
                    <td class="p-3 text-right font-mono">{{ "%.0f"|format(r.adx) if r.adx else "-" }}</td>
                    <td class="p-3 text-right font-mono">{{ "%.1f"|format(r.volume_ratio) }}x</td>
                    <td class="p-3 text-gray-400 text-xs">{{ r.sector }}</td>
                    <td class="p-3 text-gray-400 text-xs">{{ r.buy_reasons[:2]|join("; ") if r.buy_reasons else r.sell_reasons[:2]|join("; ") }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <p class="text-xs text-gray-600">
        Scanned at {{ scan.time.strftime('%d %b %Y, %I:%M %p') }} &bull;
        {{ scan.total }} stocks &bull; {{ scan.failed }} failed
    </p>

    <script>
    function filterSignals(type) {
        document.querySelectorAll('.stock-row').forEach(row => {
            const signal = row.dataset.signal;
            if (type === 'all') { row.style.display = ''; }
            else if (type === 'buy') { row.style.display = (signal === 'STRONG BUY' || signal === 'BUY') ? '' : 'none'; }
            else if (type === 'watch') { row.style.display = signal === 'WATCH' ? '' : 'none'; }
            else if (type === 'sell') { row.style.display = (signal === 'SELL' || signal === 'STRONG SELL') ? '' : 'none'; }
        });
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }

    function searchTable(query) {
        query = query.toLowerCase();
        document.querySelectorAll('.stock-row').forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(query) ? '' : 'none';
        });
    }
    </script>

    {% else %}
    <div class="card p-12 text-center">
        <p class="text-gray-400">Loading scan results...</p>
    </div>
    {% endif %}
</div>
```

**Step 2: Commit**

```bash
git add templates/scanner.html
git commit -m "feat: add scanner page with filterable results table"
```

---

### Task 5: Create Stock Detail page with chart

**Files:**
- Create: `templates/stock_detail.html`

**Step 1: Create stock detail template**

Interactive candlestick chart via Lightweight Charts + indicators, S/R levels, position sizing.

```html
{% if error is defined and error %}
<div class="card p-12 text-center">
    <p class="text-red-400">{{ error }}</p>
    <a href="/scan" hx-get="/scan" hx-target="#main-content" hx-push-url="true"
       class="text-accent hover:underline text-sm mt-4 inline-block">Back to Scanner</a>
</div>
{% elif detail %}
{% set d = detail %}
{% set a = d.analysis %}
{% set ind = d.indicators %}

<div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
        <div>
            <a href="/scan" hx-get="/scan" hx-target="#main-content" hx-push-url="true"
               class="text-gray-500 text-xs hover:text-accent">&larr; Back to Scanner</a>
            <h2 class="text-2xl font-bold text-white mt-1">
                {{ d.name }}
                <span class="text-accent font-mono text-lg">{{ d.symbol }}</span>
            </h2>
            <p class="text-gray-500 text-sm">{{ d.sector }} &bull; {{ "☪ Shariah" if d.shariah else "Non-Shariah" }}</p>
        </div>
        <div class="text-right">
            <p class="text-3xl font-bold text-white">RM {{ "%.2f"|format(d.close) }}</p>
            <span class="px-3 py-1 rounded text-sm font-bold mt-1 inline-block
                {% if a.signal == 'STRONG BUY' %}signal-strong-buy
                {% elif a.signal == 'BUY' %}signal-buy
                {% elif a.signal == 'WATCH' %}signal-watch
                {% elif a.signal == 'SELL' %}signal-sell
                {% elif a.signal == 'STRONG SELL' %}signal-strong-sell
                {% else %}signal-hold{% endif %}">
                {{ a.signal }} ({{ a.net_score }})
            </span>
        </div>
    </div>

    <!-- Chart -->
    <div class="card p-4">
        <div id="stock-chart" style="height: 400px;"></div>
    </div>

    <!-- Info Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">

        <!-- Indicators -->
        <div class="card p-4">
            <h3 class="text-sm font-semibold text-gray-400 uppercase mb-3">Indicators</h3>
            <div class="space-y-2 text-sm">
                <div class="flex justify-between"><span class="text-gray-500">EMA 20</span><span class="font-mono">{{ "%.3f"|format(ind.ema_20) if ind.ema_20 else "-" }}</span></div>
                <div class="flex justify-between"><span class="text-gray-500">EMA 50</span><span class="font-mono">{{ "%.3f"|format(ind.ema_50) if ind.ema_50 else "-" }}</span></div>
                <div class="flex justify-between"><span class="text-gray-500">EMA 200</span><span class="font-mono">{{ "%.3f"|format(ind.ema_200) if ind.ema_200 else "-" }}</span></div>
                <hr class="border-surface-100">
                <div class="flex justify-between"><span class="text-gray-500">RSI (14)</span><span class="font-mono {% if ind.rsi and ind.rsi > 70 %}text-red-400{% elif ind.rsi and ind.rsi < 30 %}text-green-400{% endif %}">{{ "%.1f"|format(ind.rsi) if ind.rsi else "-" }}</span></div>
                <div class="flex justify-between"><span class="text-gray-500">MACD Hist</span><span class="font-mono {% if ind.macd_hist and ind.macd_hist > 0 %}text-green-400{% elif ind.macd_hist and ind.macd_hist < 0 %}text-red-400{% endif %}">{{ "%.4f"|format(ind.macd_hist) if ind.macd_hist else "-" }}</span></div>
                <div class="flex justify-between"><span class="text-gray-500">ADX</span><span class="font-mono">{{ "%.1f"|format(ind.adx) if ind.adx else "-" }}</span></div>
                <div class="flex justify-between"><span class="text-gray-500">Volume Ratio</span><span class="font-mono">{{ "%.1f"|format(d.volume_ratio) }}x</span></div>
                <div class="flex justify-between"><span class="text-gray-500">ATR</span><span class="font-mono">{{ "%.4f"|format(ind.atr) if ind.atr else "-" }}</span></div>
                <hr class="border-surface-100">
                <div class="flex justify-between"><span class="text-gray-500">52w High</span><span class="font-mono">{{ "%.3f"|format(ind.high_52w) if ind.high_52w else "-" }}</span></div>
                <div class="flex justify-between"><span class="text-gray-500">52w Low</span><span class="font-mono">{{ "%.3f"|format(ind.low_52w) if ind.low_52w else "-" }}</span></div>
            </div>
        </div>

        <!-- Signals -->
        <div class="card p-4">
            <h3 class="text-sm font-semibold text-gray-400 uppercase mb-3">Signals</h3>
            {% if a.buy_reasons %}
            <div class="mb-3">
                <p class="text-xs text-green-500 font-semibold mb-1">BULLISH</p>
                {% for r in a.buy_reasons %}
                <p class="text-sm text-gray-300 flex items-start gap-1.5 mb-1">
                    <span class="text-green-400 mt-0.5">&#10003;</span> {{ r }}
                </p>
                {% endfor %}
            </div>
            {% endif %}
            {% if a.sell_reasons %}
            <div class="mb-3">
                <p class="text-xs text-red-500 font-semibold mb-1">BEARISH</p>
                {% for r in a.sell_reasons %}
                <p class="text-sm text-gray-300 flex items-start gap-1.5 mb-1">
                    <span class="text-red-400 mt-0.5">&#10007;</span> {{ r }}
                </p>
                {% endfor %}
            </div>
            {% endif %}

            {% if d.mtf.desc %}
            <div class="mt-3 pt-3 border-t border-surface-100">
                <p class="text-xs text-gray-500 font-semibold mb-1">MULTI-TIMEFRAME</p>
                <p class="text-sm {% if d.mtf.score > 0 %}text-green-400{% elif d.mtf.score < 0 %}text-red-400{% else %}text-yellow-400{% endif %}">
                    {{ d.mtf.desc }} ({{ "%+d"|format(d.mtf.score) }})
                </p>
            </div>
            {% endif %}
        </div>

        <!-- S/R + Sizing -->
        <div class="card p-4 space-y-4">
            <!-- Support/Resistance -->
            {% set sr = d.support_resistance %}
            {% if sr.support or sr.resistance %}
            <div>
                <h3 class="text-sm font-semibold text-gray-400 uppercase mb-2">Support / Resistance</h3>
                {% if sr.resistance %}
                <div class="mb-2">
                    <p class="text-xs text-red-500 mb-1">Resistance</p>
                    {% for r in sr.resistance %}
                    <span class="inline-block px-2 py-0.5 bg-red-900/30 text-red-400 rounded text-xs font-mono mr-1 mb-1">RM {{ "%.3f"|format(r) }}</span>
                    {% endfor %}
                </div>
                {% endif %}
                {% if sr.support %}
                <div>
                    <p class="text-xs text-green-500 mb-1">Support</p>
                    {% for s in sr.support %}
                    <span class="inline-block px-2 py-0.5 bg-green-900/30 text-green-400 rounded text-xs font-mono mr-1 mb-1">RM {{ "%.3f"|format(s) }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endif %}

            <!-- Position Sizing -->
            {% set sz = d.sizing %}
            {% if sz.lots > 0 %}
            <div>
                <h3 class="text-sm font-semibold text-gray-400 uppercase mb-2">Position Size</h3>
                <p class="text-xs text-gray-500 mb-2">Capital: RM 10,000</p>
                <div class="space-y-1 text-sm">
                    <div class="flex justify-between"><span class="text-gray-500">Lots</span><span class="font-mono font-bold text-white">{{ sz.lots }} ({{ sz.shares }} shares)</span></div>
                    <div class="flex justify-between"><span class="text-gray-500">Amount</span><span class="font-mono">RM {{ "%.2f"|format(sz.amount) }}</span></div>
                    <div class="flex justify-between"><span class="text-gray-500">% of Capital</span><span class="font-mono">{{ "%.1f"|format(sz.pct_of_capital) }}%</span></div>
                    <div class="flex justify-between"><span class="text-gray-500">Risk (10% SL)</span><span class="font-mono text-red-400">RM {{ "%.2f"|format(sz.risk_amount) }}</span></div>
                </div>
            </div>
            {% endif %}

            <!-- Volume Spike -->
            {% if d.spike %}
            <div class="pt-3 border-t border-surface-100">
                <p class="text-xs text-yellow-500 font-semibold mb-1">VOLUME SPIKE</p>
                <p class="text-sm text-yellow-400 font-mono">{{ "%.1f"|format(d.spike.volume_ratio) }}x avg &bull; {{ d.spike.type }}</p>
            </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Chart initialization -->
<script>
(function() {
    const container = document.getElementById('stock-chart');
    if (!container) return;

    const chart = LightweightCharts.createChart(container, {
        layout: { background: { color: '#1e293b' }, textColor: '#94a3b8' },
        grid: { vertLines: { color: '#334155' }, horzLines: { color: '#334155' } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: '#334155' },
        timeScale: { borderColor: '#334155', timeVisible: false },
    });

    const candleSeries = chart.addCandlestickSeries({
        upColor: '#22c55e', downColor: '#ef4444',
        borderUpColor: '#22c55e', borderDownColor: '#ef4444',
        wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    });

    const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
    });

    fetch('/api/chart/{{ d.symbol }}')
        .then(r => r.json())
        .then(data => {
            candleSeries.setData(data.candles);
            volumeSeries.setData(data.volume);

            if (data.ema20.length) {
                chart.addLineSeries({ color: '#f59e0b', lineWidth: 1, title: 'EMA20' }).setData(data.ema20);
            }
            if (data.ema50.length) {
                chart.addLineSeries({ color: '#3b82f6', lineWidth: 1, title: 'EMA50' }).setData(data.ema50);
            }
            if (data.ema200.length) {
                chart.addLineSeries({ color: '#a855f7', lineWidth: 1, title: 'EMA200' }).setData(data.ema200);
            }
            if (data.bb_upper.length) {
                chart.addLineSeries({ color: 'rgba(156,163,175,0.3)', lineWidth: 1, lineStyle: 2 }).setData(data.bb_upper);
                chart.addLineSeries({ color: 'rgba(156,163,175,0.3)', lineWidth: 1, lineStyle: 2 }).setData(data.bb_lower);
            }

            chart.timeScale().fitContent();
        });

    // Resize handler
    const ro = new ResizeObserver(() => {
        chart.applyOptions({ width: container.clientWidth });
    });
    ro.observe(container);

    // Cleanup on HTMX navigation
    document.body.addEventListener('htmx:beforeSwap', function cleanup() {
        ro.disconnect();
        chart.remove();
        document.body.removeEventListener('htmx:beforeSwap', cleanup);
    });
})();
</script>
{% endif %}
```

**Step 2: Commit**

```bash
git add templates/stock_detail.html
git commit -m "feat: add stock detail page with interactive candlestick chart"
```

---

### Task 6: Create Sectors page

**Files:**
- Create: `templates/sectors.html`

**Step 1: Create sectors template**

```html
<div class="space-y-4">
    <h2 class="text-2xl font-bold text-white">Sector Rotation</h2>

    {% if sectors %}
    <div class="card overflow-hidden">
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-500 text-xs uppercase bg-surface-100">
                    <th class="text-left p-3">#</th>
                    <th class="text-left p-3">Sector</th>
                    <th class="text-left p-3">Trend</th>
                    <th class="text-right p-3">Avg Score</th>
                    <th class="text-right p-3">1M Change</th>
                    <th class="text-right p-3">Avg RSI</th>
                    <th class="text-right p-3">Stocks</th>
                    <th class="text-right p-3 text-green-400">BUY</th>
                    <th class="text-right p-3 text-red-400">SELL</th>
                    <th class="text-left p-3">Top Pick</th>
                </tr>
            </thead>
            <tbody>
                {% for s in sectors %}
                <tr class="border-t border-surface-100 hover:bg-surface-100">
                    <td class="p-3 text-gray-500">{{ loop.index }}</td>
                    <td class="p-3 font-medium text-white">{{ s.sector }}</td>
                    <td class="p-3">
                        {% if 'HOT' in s.trend %}
                        <span class="text-green-400 font-semibold">{{ s.trend }}</span>
                        {% elif 'WARM' in s.trend %}
                        <span class="text-yellow-400">{{ s.trend }}</span>
                        {% elif 'COLD' in s.trend %}
                        <span class="text-red-400">{{ s.trend }}</span>
                        {% else %}
                        <span class="text-gray-500">{{ s.trend }}</span>
                        {% endif %}
                    </td>
                    <td class="p-3 text-right font-mono">{{ "%.0f"|format(s.avg_score) }}</td>
                    <td class="p-3 text-right font-mono {% if s.avg_pct_1m > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                        {{ "%+.1f"|format(s.avg_pct_1m) }}%
                    </td>
                    <td class="p-3 text-right font-mono">{{ "%.0f"|format(s.avg_rsi) }}</td>
                    <td class="p-3 text-right">{{ s.stock_count }}</td>
                    <td class="p-3 text-right text-green-400">{{ s.buy_signals }}</td>
                    <td class="p-3 text-right text-red-400">{{ s.sell_signals }}</td>
                    <td class="p-3">
                        <a hx-get="/stock/{{ s.top_stock.symbol }}" hx-target="#main-content" hx-push-url="true"
                           class="text-accent hover:underline cursor-pointer font-mono text-xs">
                            {{ s.top_stock.symbol }} ({{ "%+d"|format(s.top_stock.net_score) }})
                        </a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <p class="text-xs text-gray-600">🟢 HOT = Strong sector momentum &bull; 🔴 COLD = Weak / avoid</p>
    {% else %}
    <div class="card p-12 text-center">
        <p class="text-gray-400">Run a scan first to see sector data.</p>
        <button hx-get="/scan" hx-target="#main-content" hx-push-url="/scan"
                class="mt-4 px-4 py-2 bg-accent text-white rounded-lg text-sm">🔍 Run Scan</button>
    </div>
    {% endif %}
</div>
```

**Step 2: Commit**

```bash
git add templates/sectors.html
git commit -m "feat: add sector rotation page"
```

---

### Task 7: Create Volume Spikes page

**Files:**
- Create: `templates/spikes.html`

**Step 1: Create spikes template**

```html
<div class="space-y-4">
    <h2 class="text-2xl font-bold text-white">Volume Spikes</h2>
    <p class="text-sm text-gray-500">Stocks with unusual volume (&gt;2.5x average) — possible institutional activity</p>

    {% if spikes %}
    <div class="card overflow-hidden">
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-500 text-xs uppercase bg-surface-100">
                    <th class="text-left p-3">Symbol</th>
                    <th class="text-left p-3">Name</th>
                    <th class="text-right p-3">Price (RM)</th>
                    <th class="text-right p-3">Vol Ratio</th>
                    <th class="text-right p-3">Price Change</th>
                    <th class="text-left p-3">Type</th>
                </tr>
            </thead>
            <tbody>
                {% for s in spikes %}
                <tr class="border-t border-surface-100 hover:bg-surface-100 cursor-pointer"
                    hx-get="/stock/{{ s.symbol }}" hx-target="#main-content" hx-push-url="true">
                    <td class="p-3 text-accent font-mono">{{ s.symbol }}</td>
                    <td class="p-3">{{ s.name }}</td>
                    <td class="p-3 text-right font-mono">{{ "%.2f"|format(s.close) }}</td>
                    <td class="p-3 text-right font-mono font-bold text-yellow-400">{{ "%.1f"|format(s.spike.volume_ratio) }}x</td>
                    <td class="p-3 text-right font-mono {% if s.spike.price_change > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                        {{ "%+.1f"|format(s.spike.price_change) }}%
                    </td>
                    <td class="p-3">
                        {% if 'Bullish' in s.spike.type %}
                        <span class="text-green-400">{{ s.spike.type }}</span>
                        {% else %}
                        <span class="text-red-400">{{ s.spike.type }}</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <p class="text-xs text-gray-600">Found {{ spikes|length }} stocks with unusual volume</p>
    {% else %}
    <div class="card p-12 text-center">
        <p class="text-gray-400">No volume spikes detected. Run a scan first.</p>
        <button hx-get="/scan" hx-target="#main-content" hx-push-url="/scan"
                class="mt-4 px-4 py-2 bg-accent text-white rounded-lg text-sm">🔍 Run Scan</button>
    </div>
    {% endif %}
</div>
```

**Step 2: Commit**

```bash
git add templates/spikes.html
git commit -m "feat: add volume spikes page"
```

---

### Task 8: Create Portfolio page

**Files:**
- Create: `templates/portfolio.html`

**Step 1: Create portfolio template**

```html
<div class="space-y-4">
    <h2 class="text-2xl font-bold text-white">Portfolio</h2>

    <!-- Add Stock Form -->
    <div class="card p-4">
        <h3 class="text-sm font-semibold text-gray-400 uppercase mb-3">Add Stock</h3>
        <form hx-post="/portfolio/add" hx-target="#main-content" class="flex gap-3 items-end">
            <div>
                <label class="text-xs text-gray-500 block mb-1">Symbol</label>
                <input type="text" name="symbol" placeholder="e.g. 1155" required
                       class="px-3 py-2 bg-surface-100 border border-surface-200 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-accent w-32">
            </div>
            <div>
                <label class="text-xs text-gray-500 block mb-1">Buy Price (RM)</label>
                <input type="number" name="price" step="0.01" required placeholder="0.00"
                       class="px-3 py-2 bg-surface-100 border border-surface-200 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-accent w-32">
            </div>
            <div>
                <label class="text-xs text-gray-500 block mb-1">Quantity</label>
                <input type="number" name="quantity" value="100" step="100"
                       class="px-3 py-2 bg-surface-100 border border-surface-200 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-accent w-28">
            </div>
            <button type="submit"
                    class="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 transition">
                + Add
            </button>
        </form>
    </div>

    {% if holdings %}
    <!-- Holdings Table -->
    <div class="card overflow-hidden">
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-500 text-xs uppercase bg-surface-100">
                    <th class="text-left p-3">Symbol</th>
                    <th class="text-left p-3">Name</th>
                    <th class="text-right p-3">Buy Price</th>
                    <th class="text-right p-3">Current</th>
                    <th class="text-right p-3">P/L %</th>
                    <th class="text-center p-3">Signal</th>
                    <th class="text-right p-3">Score</th>
                    <th class="text-left p-3">Action</th>
                    <th class="text-center p-3"></th>
                </tr>
            </thead>
            <tbody>
                {% for h in holdings %}
                <tr class="border-t border-surface-100 hover:bg-surface-100">
                    <td class="p-3 text-accent font-mono cursor-pointer"
                        hx-get="/stock/{{ h.symbol }}" hx-target="#main-content" hx-push-url="true">
                        {{ h.symbol }}
                    </td>
                    <td class="p-3">{{ h.name }}</td>
                    <td class="p-3 text-right font-mono">{{ "%.2f"|format(h.buy_price) }}</td>
                    <td class="p-3 text-right font-mono">{{ "%.2f"|format(h.current) if h.current else "-" }}</td>
                    <td class="p-3 text-right font-mono font-bold {% if h.pnl is not none and h.pnl >= 0 %}text-green-400{% elif h.pnl is not none %}text-red-400{% endif %}">
                        {{ "%+.1f"|format(h.pnl) if h.pnl is not none else "-" }}%
                    </td>
                    {% if h.analysis %}
                    <td class="p-3 text-center">
                        <span class="px-2 py-0.5 rounded text-xs font-bold
                            {% if h.analysis.signal == 'STRONG BUY' %}signal-strong-buy
                            {% elif h.analysis.signal == 'BUY' %}signal-buy
                            {% elif h.analysis.signal == 'WATCH' %}signal-watch
                            {% elif h.analysis.signal == 'SELL' %}signal-sell
                            {% elif h.analysis.signal == 'STRONG SELL' %}signal-strong-sell
                            {% else %}signal-hold{% endif %}">
                            {{ h.analysis.signal }}
                        </span>
                    </td>
                    <td class="p-3 text-right font-mono">{{ h.analysis.net_score }}</td>
                    <td class="p-3 text-xs text-gray-400">
                        {% if h.analysis.signal in ['SELL', 'STRONG SELL'] %}
                        <span class="text-red-400">{{ h.analysis.sell_reasons[:2]|join("; ") }}</span>
                        {% elif h.analysis.signal in ['BUY', 'STRONG BUY'] %}
                        <span class="text-green-400">Hold / Add</span>
                        {% else %}
                        Monitor
                        {% endif %}
                    </td>
                    {% else %}
                    <td class="p-3 text-center text-gray-500">-</td>
                    <td class="p-3 text-right text-gray-500">-</td>
                    <td class="p-3 text-gray-500">No data</td>
                    {% endif %}
                    <td class="p-3 text-center">
                        <form hx-post="/portfolio/remove" hx-target="#main-content" class="inline">
                            <input type="hidden" name="symbol" value="{{ h.symbol }}">
                            <button type="submit" class="text-gray-600 hover:text-red-400 text-xs" title="Remove">✕</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Sell Alerts -->
    {% set sell_alerts = holdings|selectattr("analysis")|selectattr("analysis.signal", "in", ["SELL", "STRONG SELL"])|list %}
    {% if sell_alerts %}
    <div class="card p-4 border-red-900/50">
        <h3 class="text-sm font-semibold text-red-400 uppercase mb-2">Sell Alerts</h3>
        {% for h in sell_alerts %}
        <p class="text-sm text-gray-300 mb-1">
            <span class="text-red-400 font-mono">{{ h.symbol }}</span> ({{ h.name }}) &mdash;
            {{ h.analysis.sell_reasons[:2]|join("; ") }}
        </p>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-sm text-green-400">No sell alerts. All positions look okay.</p>
    {% endif %}

    {% else %}
    <div class="card p-8 text-center">
        <p class="text-gray-400">No stocks in portfolio yet. Use the form above to add your first stock.</p>
    </div>
    {% endif %}
</div>
```

**Step 2: Commit**

```bash
git add templates/portfolio.html
git commit -m "feat: add portfolio page with holdings, P/L tracking, and sell alerts"
```

---

### Task 9: Create Signal Tracker page

**Files:**
- Create: `templates/tracker.html`

**Step 1: Create tracker template**

```html
<div class="space-y-4">
    <h2 class="text-2xl font-bold text-white">Signal Tracker</h2>
    <p class="text-sm text-gray-500">How accurate are Stock Hunter's signals? Track performance at 7, 14, and 30 days.</p>

    {% if stats.total_signals > 0 %}

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        {% for period in ['7d', '14d', '30d'] %}
        {% set s = stats[period] %}
        <div class="card p-4">
            <h3 class="text-sm font-semibold text-gray-400 uppercase mb-3">{{ period }} Performance</h3>
            {% if s.count > 0 %}
            <div class="space-y-2">
                <div class="flex justify-between">
                    <span class="text-gray-500 text-sm">Signals</span>
                    <span class="font-mono text-white">{{ s.count }}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-500 text-sm">Win Rate</span>
                    <span class="font-mono font-bold {% if s.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">
                        {{ s.win_rate }}%
                    </span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-500 text-sm">Avg Return</span>
                    <span class="font-mono {% if s.avg_return >= 0 %}text-green-400{% else %}text-red-400{% endif %}">
                        {{ "%+.2f"|format(s.avg_return) }}%
                    </span>
                </div>
                {% if s.best %}
                <div class="flex justify-between">
                    <span class="text-gray-500 text-sm">Best</span>
                    <span class="font-mono text-green-400">{{ s.best.symbol }} ({{ "%+.2f"|format(s.best.pnl) }}%)</span>
                </div>
                {% endif %}
                {% if s.worst %}
                <div class="flex justify-between">
                    <span class="text-gray-500 text-sm">Worst</span>
                    <span class="font-mono text-red-400">{{ s.worst.symbol }} ({{ "%+.2f"|format(s.worst.pnl) }}%)</span>
                </div>
                {% endif %}
            </div>
            {% else %}
            <p class="text-gray-500 text-sm">No data yet</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <!-- Recent Signals -->
    {% if recent %}
    <div class="card overflow-hidden">
        <div class="p-3 bg-surface-100">
            <h3 class="text-sm font-semibold text-gray-400 uppercase">Recent Signals</h3>
        </div>
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-500 text-xs uppercase">
                    <th class="text-left p-3">Date</th>
                    <th class="text-left p-3">Symbol</th>
                    <th class="text-left p-3">Name</th>
                    <th class="text-center p-3">Signal</th>
                    <th class="text-right p-3">Entry</th>
                    <th class="text-right p-3">7d</th>
                    <th class="text-right p-3">14d</th>
                    <th class="text-right p-3">30d</th>
                </tr>
            </thead>
            <tbody>
                {% for sig in recent %}
                <tr class="border-t border-surface-100 hover:bg-surface-100">
                    <td class="p-3 text-gray-500">{{ sig.date }}</td>
                    <td class="p-3 text-accent font-mono cursor-pointer"
                        hx-get="/stock/{{ sig.symbol }}" hx-target="#main-content" hx-push-url="true">
                        {{ sig.symbol }}
                    </td>
                    <td class="p-3">{{ sig.name }}</td>
                    <td class="p-3 text-center">
                        <span class="px-2 py-0.5 rounded text-xs font-bold signal-buy">{{ sig.signal }}</span>
                    </td>
                    <td class="p-3 text-right font-mono">{{ "%.2f"|format(sig.entry_price) }}</td>
                    {% for period in ['7d', '14d', '30d'] %}
                    <td class="p-3 text-right font-mono">
                        {% if period in sig.outcomes %}
                        <span class="{% if sig.outcomes[period].pnl_pct >= 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {{ "%+.1f"|format(sig.outcomes[period].pnl_pct) }}%
                        </span>
                        {% else %}
                        <span class="text-gray-600">-</span>
                        {% endif %}
                    </td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% else %}
    <div class="card p-12 text-center">
        <p class="text-4xl mb-4">📈</p>
        <p class="text-gray-400 mb-2">No signals tracked yet.</p>
        <p class="text-gray-500 text-sm">Run daily scans to start tracking signal accuracy.</p>
    </div>
    {% endif %}
</div>
```

**Step 2: Commit**

```bash
git add templates/tracker.html
git commit -m "feat: add signal tracker page with performance stats"
```

---

### Task 10: Create static/app.js and finalize

**Files:**
- Create: `static/app.js`

**Step 1: Create app.js**

Handles HTMX navigation active state highlighting and global utilities.

```javascript
// ── Active nav link highlighting ──
function updateActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (path === href || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
        }
    });
}

// Update on HTMX navigation
document.body.addEventListener('htmx:pushedIntoHistory', updateActiveNav);
document.body.addEventListener('htmx:afterSwap', updateActiveNav);

// Initial state
updateActiveNav();
```

**Step 2: Create directories**

```bash
mkdir -p templates static
```

**Step 3: Commit**

```bash
git add static/app.js
git commit -m "feat: add app.js with nav active state management"
```

---

### Task 11: End-to-end test

**Step 1: Start the server**

Run: `python3 app.py`
Expected: `🎯 Stock Hunter Web — http://localhost:5000`

**Step 2: Test dashboard**

Open `http://localhost:5000` in browser.
Expected: Welcome page with "Start Scanning" button.

**Step 3: Test scan**

Click "Start Scanning" or navigate to `/scan`.
Expected: Loading spinner, then table of stock results with signal badges.

**Step 4: Test stock detail**

Click any stock row.
Expected: Candlestick chart renders with EMA overlays, indicators panel, signals, S/R levels.

**Step 5: Test sectors and spikes**

Navigate to Sectors and Volume Spikes pages.
Expected: Tables render with data from the cached scan.

**Step 6: Test portfolio**

Navigate to Portfolio. Add a stock (e.g., symbol: 1155, price: 11.00, qty: 100).
Expected: Stock appears in holdings table with current price and P/L.

**Step 7: Test search API**

Navigate to `http://localhost:5000/api/search?q=maybank`
Expected: JSON array with `[{"symbol": "1155.KL", "name": "Maybank"}]`

**Step 8: Final commit**

```bash
git add -A
git commit -m "feat: Stock Hunter web dashboard - complete webapp"
```
