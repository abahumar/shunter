#!/usr/bin/env python3
"""
Stock Hunter Web - Bursa Malaysia Scanner Dashboard
Run: python app.py
"""

import time
import math
from datetime import datetime
from flask import Flask, render_template, request, jsonify

from scanner.symbols import get_all_symbols, get_symbol_name, search_symbol, SYMBOLS
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

def _run_scan(force=False):
    """Run full market scan, using cache if available."""
    cache_key = "scan_all"
    if not force:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    symbols = get_all_symbols()

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
            analysis["shariah"] = True
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
    force = request.args.get("refresh") == "1"
    scan = _run_scan(force=force)
    return _render("scanner.html", request, scan=scan)


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
            "shariah": True,
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
