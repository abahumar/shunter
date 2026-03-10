#!/usr/bin/env python3
"""
Stock Hunter Web - Bursa Malaysia Scanner Dashboard
Run: python app.py
"""

import time
import math
import threading
import pickle
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify

from scanner.symbols import get_all_symbols, get_symbol_name, search_symbol, SYMBOLS
from scanner.data_fetcher import fetch_stock_data, fetch_bulk_data, fetch_batch_download
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock, classify_net_score
from scanner.market_sentiment import fetch_market_sentiment
from scanner.db import (
    add_stock, remove_stock, get_portfolio,
    add_to_watchlist, remove_from_watchlist, get_watchlist, check_alerts,
    get_tracker_stats, get_recent_signals, log_signals, update_outcomes,
    get_win_rate_by_score,
)
from scanner.sectors import analyze_sectors, get_sector
from scanner.advanced import (
    multi_timeframe_score,
    find_support_resistance,
    detect_volume_spike,
    calculate_position_size,
    compute_risk_score,
    calculate_entry_plan,
    compute_confidence_grade,
    detect_emerging_setup,
)
from scanner.vpa import analyze_vpa
from scanner.backtest import backtest as run_backtest

app = Flask(__name__)

# ── In-memory cache ──
_cache = {}
SCAN_TTL = 86400     # 24 hours (scan results persist until manual refresh)
STOCK_TTL = 600      # 10 minutes
SCAN_SAVE_PATH = os.path.join(os.path.dirname(__file__), "data", "last_scan.pkl")
PREV_SIGNALS_PATH = os.path.join(os.path.dirname(__file__), "data", "prev_signals.pkl")

# ── Background scan state ──
_scan_progress = {
    "running": False,
    "current": 0,
    "total": 0,
    "status": "idle",       # idle | scanning | done | error
    "message": "",
}
_scan_lock = threading.Lock()


def _cache_get(key):
    """Get cached value if not expired."""
    entry = _cache.get(key)
    if entry and (time.time() - entry["time"]) < entry["ttl"]:
        return entry["data"]
    return None


def _cache_set(key, data, ttl):
    """Set cache with TTL."""
    _cache[key] = {"data": data, "time": time.time(), "ttl": ttl}


def _save_scan_to_disk(scan_result):
    """Persist scan results to disk so they survive restarts."""
    try:
        os.makedirs(os.path.dirname(SCAN_SAVE_PATH), exist_ok=True)
        with open(SCAN_SAVE_PATH, "wb") as f:
            pickle.dump(scan_result, f)
    except Exception:
        pass


def _load_scan_from_disk():
    """Load last scan results from disk into cache on startup."""
    try:
        if not os.path.exists(SCAN_SAVE_PATH):
            return
        with open(SCAN_SAVE_PATH, "rb") as f:
            scan_result = pickle.load(f)
        if scan_result and "results" in scan_result:
            _cache_set("scan_all", scan_result, SCAN_TTL)
    except Exception:
        pass


def _load_prev_signals():
    """Load previous scan signals for consecutive confirmation."""
    try:
        if os.path.exists(PREV_SIGNALS_PATH):
            with open(PREV_SIGNALS_PATH, "rb") as f:
                return pickle.load(f)
    except Exception:
        pass
    return {}


def _save_prev_signals(signals):
    """Save current signals for next scan's confirmation check."""
    try:
        os.makedirs(os.path.dirname(PREV_SIGNALS_PATH), exist_ok=True)
        with open(PREV_SIGNALS_PATH, "wb") as f:
            pickle.dump(signals, f)
    except Exception:
        pass


# Startup initialization is deferred until after all functions are defined (see below)


def _is_htmx(request):
    """Check if request is from HTMX (partial) or direct navigation (full page)."""
    return request.headers.get("HX-Request") == "true"


def _get_klci_sentiment():
    """Fetch KLCI index data for market sentiment (cached 24h)."""
    cache_key = "klci_sentiment"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        df = fetch_stock_data("^KLSE", period="1mo")
        if df is None or len(df) < 2:
            return None

        current = df["Close"].iloc[-1]
        prev = df["Close"].iloc[-2]
        change = current - prev
        change_pct = (change / prev) * 100

        ema5 = df["Close"].rolling(5).mean().iloc[-1]
        ema20 = df["Close"].rolling(20).mean().iloc[-1]

        if change_pct > 0.3:
            mood = "Bullish"
        elif change_pct < -0.3:
            mood = "Bearish"
        else:
            mood = "Neutral"

        if current > ema5 > ema20:
            trend = "Uptrend"
        elif current < ema5 < ema20:
            trend = "Downtrend"
        else:
            trend = "Sideways"

        result = {
            "price": current,
            "change": change,
            "change_pct": change_pct,
            "mood": mood,
            "trend": trend,
        }
        _cache_set(cache_key, result, SCAN_TTL)  # 24h cache
        return result
    except Exception:
        return None


def _refresh_klci_background():
    """Fetch KLCI sentiment in a background thread if not cached."""
    if _cache_get("klci_sentiment"):
        return
    thread = threading.Thread(target=_get_klci_sentiment, daemon=True)
    thread.start()


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
    total = len(symbols)

    _scan_progress["current"] = 0
    _scan_progress["total"] = total
    _scan_progress["status"] = "scanning"
    _scan_progress["message"] = "Fetching stock data (batch mode)..."

    def _on_progress(current, total_count, msg):
        _scan_progress["current"] = current
        _scan_progress["total"] = total_count
        _scan_progress["message"] = msg

    stock_data = fetch_batch_download(symbols, period="1y", chunk_size=50, on_progress=_on_progress)
    failed = total - len(stock_data)

    _scan_progress["message"] = "Checking market sentiment..."
    sentiment = fetch_market_sentiment()

    _scan_progress["message"] = "Analyzing signals..."

    results = []
    for symbol, df in stock_data.items():
        try:
            df = compute_indicators(df)
            ind = get_latest_indicators(df)
            analysis = analyze_stock(ind)

            mtf_bonus, mtf_desc = multi_timeframe_score(df)
            analysis["net_score"] += mtf_bonus
            analysis["mtf"] = mtf_desc or ""

            # Market sentiment adjustment
            analysis["net_score"] += sentiment["score_adj"]

            analysis["symbol"] = symbol
            analysis["name"] = get_symbol_name(symbol)
            analysis["close"] = ind.get("close", 0)
            analysis["rsi"] = ind.get("rsi", 0)
            analysis["adx"] = ind.get("adx", 0)
            analysis["shariah"] = True
            analysis["sector"] = get_sector(symbol)

            # Trailing 12-month dividend yield
            try:
                div_total = df["Dividends"].sum() if "Dividends" in df.columns else 0
                analysis["div_yield"] = (div_total / ind["close"] * 100) if ind["close"] > 0 and div_total > 0 else 0
            except Exception:
                analysis["div_yield"] = 0

            vol_sma = ind.get("volume_sma_20", 0)
            analysis["volume_ratio"] = (
                ind["volume"] / vol_sma if vol_sma and vol_sma > 0 else 0
            )

            spike = detect_volume_spike(df)
            analysis["spike"] = spike

            risk = compute_risk_score(ind)
            analysis["risk_level"] = risk["level"]
            analysis["risk_warnings"] = risk["warnings"]

            # Volume Price Analysis
            vpa = analyze_vpa(df)
            analysis["vpa_score"] = vpa["vpa_score"]
            analysis["vpa_bias"] = vpa["vpa_bias"]
            analysis["vpa_pattern"] = vpa["latest_pattern"]
            analysis["vpa_patterns"] = vpa["patterns"]
            # VPA score contributes to net score (capped at ±15)
            vpa_adj = max(-15, min(15, vpa["vpa_score"]))
            analysis["net_score"] += vpa_adj

            results.append(analysis)
        except Exception:
            continue

    # Consecutive signal confirmation: compare with previous scan
    prev_signals = _load_prev_signals()
    for r in results:
        # Reclassify signal based on adjusted net_score (MTF + sentiment)
        r["signal"] = classify_net_score(r["net_score"])
        # Check if stock was also BUY in previous scan
        r["confirmed"] = (
            r["signal"] in ("STRONG BUY", "BUY")
            and prev_signals.get(r["symbol"]) in ("STRONG BUY", "BUY")
        )
        if r["confirmed"]:
            r["net_score"] += 10
            r["signal"] = classify_net_score(r["net_score"])

    # Compute confidence grade for each result
    for r in results:
        grade_info = compute_confidence_grade(
            net_score=r["net_score"],
            volume_ratio=r.get("volume_ratio", 0),
            mtf_desc=r.get("mtf", ""),
            risk_level=r.get("risk_level", "Medium"),
            confirmed=r.get("confirmed", False),
        )
        r["grade"] = grade_info["grade"]
        r["grade_label"] = grade_info["label"]
        r["grade_points"] = grade_info["points"]
        r["grade_factors"] = grade_info["factors"]

        # Detect emerging setups (Grade C/D stocks trending toward B/A)
        r["emerging"] = False
        r["emerging_reasons"] = []
        if r["grade"] in ("C", "D", "F"):
            symbol = r["symbol"]
            df = stock_data.get(symbol)
            if df is not None and len(df) >= 50:
                try:
                    ind = get_latest_indicators(df)
                    emerging = detect_emerging_setup(df, ind, r["net_score"], r["grade"])
                    if emerging:
                        r["emerging"] = True
                        r["emerging_reasons"] = emerging["reasons"]
                        r["emerging_points"] = emerging["points"]
                except Exception:
                    pass

        # Strategy match: Grade A/B with BUY+, or Grade C emerging with BUY+
        is_buy = r["signal"] in ("STRONG BUY", "BUY")
        r["strategy_match"] = is_buy and (
            r["grade"] in ("A", "B") or
            (r["grade"] == "C" and r["emerging"])
        )

    # Save current signals for next scan's confirmation
    _save_prev_signals({r["symbol"]: r["signal"] for r in results})

    results.sort(key=lambda x: x["net_score"], reverse=True)

    scan_result = {
        "results": results,
        "total": len(results),
        "failed": failed,
        "time": datetime.now(),
        "stock_data": stock_data,
        "sentiment": sentiment,
    }
    _cache_set(cache_key, scan_result, SCAN_TTL)
    _save_scan_to_disk(scan_result)

    # Log BUY signals to tracker and update past outcomes
    buy_signals = [r for r in results if r["signal"] in ("BUY", "STRONG BUY")]
    log_signals(buy_signals)
    update_outcomes()

    _scan_progress["status"] = "done"
    _scan_progress["running"] = False
    _scan_progress["message"] = "Scan complete"

    return scan_result


def _start_background_scan(force=False):
    """Launch scan in a background thread if not already running."""
    with _scan_lock:
        if _scan_progress["running"]:
            return  # already running
        _scan_progress["running"] = True

    def _worker():
        try:
            _run_scan(force=force)
        except Exception as e:
            _scan_progress["status"] = "error"
            _scan_progress["message"] = str(e)
            _scan_progress["running"] = False

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ── Startup initialization ──
_load_scan_from_disk()
_refresh_klci_background()


# ── Routes ──

@app.route("/")
def dashboard():
    """Dashboard with summary cards."""
    scan = _cache_get("scan_all")
    klci = _get_klci_sentiment()
    return _render("dashboard.html", request, scan=scan, klci=klci)


@app.route("/scan")
def scan():
    """Full scan results page."""
    force = request.args.get("refresh") == "1"

    # If cached results exist (and not forcing refresh), show them immediately
    if not force:
        cached = _cache_get("scan_all")
        if cached:
            return _render("scanner.html", request, scan=cached)

    # Start background scan if not already running
    _start_background_scan(force=force)
    return _render("scan_progress.html", request)


@app.route("/scan/status")
def scan_status():
    """Return scan progress — used by HTMX polling."""
    # If scan is done, return the full scanner results
    if _scan_progress["status"] == "done":
        scan_data = _cache_get("scan_all")
        if scan_data:
            return render_template("scanner.html", scan=scan_data, now=datetime.now())

    # Otherwise return progress partial
    return render_template("scan_progress_partial.html",
                           progress=_scan_progress, now=datetime.now())


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
        risk = compute_risk_score(ind)
        entry_plan = calculate_entry_plan(ind["close"], ind.get("atr", 0))

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
            "risk": risk,
            "entry_plan": entry_plan,
            "sector": get_sector(symbol),
            "shariah": True,
            "volume_ratio": vol_ratio,
        }
        _cache_set(cache_key, detail, STOCK_TTL)

    return _render("stock_detail.html", request, detail=detail, symbol=symbol)


@app.route("/sectors")
def sectors():
    """Sector rotation view — uses pre-computed scan results (fast)."""
    scan = _cache_get("scan_all")
    if not scan:
        _start_background_scan()
        return _render("scan_progress.html", request)

    # Build sector data from pre-computed scan results instead of re-analyzing
    sector_stocks = {}
    for r in scan.get("results", []):
        sector = r.get("sector", "Unknown")
        if sector not in sector_stocks:
            sector_stocks[sector] = []
        sector_stocks[sector].append(r)

    sector_data = []
    for sector, stocks in sector_stocks.items():
        if not stocks:
            continue
        avg_score = sum(s["net_score"] for s in stocks) / len(stocks)
        avg_rsi = sum(s.get("rsi", 50) or 50 for s in stocks) / len(stocks)
        buy_count = sum(1 for s in stocks if s["signal"] in ("BUY", "STRONG BUY"))
        sell_count = sum(1 for s in stocks if s["signal"] in ("SELL", "STRONG SELL"))

        # Estimate 1-month change from stock_data if available
        avg_pct = 0
        pct_count = 0
        for s in stocks:
            sdf = scan["stock_data"].get(s["symbol"])
            if sdf is not None and len(sdf) >= 20:
                try:
                    pct = ((s["close"] - sdf.iloc[-20]["Close"]) / sdf.iloc[-20]["Close"]) * 100
                    avg_pct += pct
                    pct_count += 1
                except Exception:
                    pass
        avg_pct = avg_pct / pct_count if pct_count > 0 else 0

        if avg_score >= 30:
            trend = "🟢 HOT"
        elif avg_score >= 10:
            trend = "🟡 WARM"
        elif avg_score >= -10:
            trend = "⚪ NEUTRAL"
        else:
            trend = "🔴 COLD"

        top = max(stocks, key=lambda s: s["net_score"])
        sector_data.append({
            "sector": sector,
            "trend": trend,
            "avg_score": avg_score,
            "avg_rsi": avg_rsi,
            "avg_pct_1m": avg_pct,
            "stock_count": len(stocks),
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "top_stock": {"symbol": top["symbol"], "close": top["close"],
                          "net_score": top["net_score"], "signal": top["signal"]},
        })

    sector_data.sort(key=lambda x: x["avg_score"], reverse=True)
    return _render("sectors.html", request, sectors=sector_data, scan=scan)


@app.route("/spikes")
def spikes():
    """Volume spikes page."""
    scan = _cache_get("scan_all")
    if not scan:
        _start_background_scan()
        return _render("scan_progress.html", request)

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
            holdings.append({**stock, "name": get_symbol_name(symbol), "current": None, "pnl": None, "analysis": None, "stop_loss": None, "risk": None})
            continue

        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        analysis = analyze_stock(ind)
        current = ind["close"]
        pnl = ((current - stock["buy_price"]) / stock["buy_price"]) * 100
        risk = compute_risk_score(ind)
        atr = ind.get("atr", 0)
        stop_price = current - (2 * atr) if atr else stock["buy_price"] * 0.9

        holdings.append({
            **stock,
            "name": get_symbol_name(symbol),
            "current": current,
            "pnl": pnl,
            "analysis": analysis,
            "risk": risk,
            "stop_loss": max(stop_price, 0.005),
        })

    # Compute portfolio summary
    active = [h for h in holdings if h.get("current")]
    total_invested = sum(h["buy_price"] * h.get("quantity", 0) for h in active if h.get("quantity"))
    total_current = sum(h["current"] * h.get("quantity", 0) for h in active if h.get("quantity"))
    total_risk = sum((h["current"] - h["stop_loss"]) * h.get("quantity", 0) for h in active if h.get("quantity") and h.get("stop_loss"))
    avg_pnl = sum(h["pnl"] for h in active) / len(active) if active else 0
    sell_count = len([h for h in active if h.get("analysis") and h["analysis"]["signal"] in ("SELL", "STRONG SELL")])
    high_risk_count = len([h for h in active if h.get("risk") and h["risk"]["level"] == "High"])
    worst = min(active, key=lambda h: h.get("pnl", 0)) if active else None

    summary = {
        "total_invested": total_invested,
        "total_current": total_current,
        "total_risk": total_risk,
        "avg_pnl": avg_pnl,
        "sell_count": sell_count,
        "high_risk_count": high_risk_count,
        "worst": worst,
        "count": len(active),
    }

    return _render("portfolio.html", request, holdings=holdings, summary=summary)


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
    score_ranges = get_win_rate_by_score()
    return _render("tracker.html", request, stats=stats, recent=recent, score_ranges=score_ranges)


@app.route("/backtest")
def backtest_page():
    """Backtest page — form + results."""
    scan = _cache_get("scan_all")
    has_data = scan is not None
    return _render("backtest.html", request, has_data=has_data, result=None)


@app.route("/manual")
def manual():
    """User manual page."""
    return _render("manual.html", request)


@app.route("/backtest/run", methods=["POST"])
def backtest_run():
    """Run backtest with submitted parameters."""
    scan = _cache_get("scan_all")
    if not scan:
        return _render("backtest.html", request, has_data=False, result=None,
                       error="Run a scan first to load stock data.")

    lookback = int(request.form.get("lookback", 60))
    top_n = int(request.form.get("top_n", 10))
    scan_interval = int(request.form.get("scan_interval", 5))
    stop_loss = float(request.form.get("stop_loss", -7))
    min_price = float(request.form.get("min_price", 0.10))
    max_price = float(request.form.get("max_price", 0))
    signal_filter = request.form.get("signal_filter", "BUY")
    capital = float(request.form.get("capital", 10000))
    volume_confirm = request.form.get("volume_confirm") == "on"
    trend_confirm = request.form.get("trend_confirm") == "on"
    take_profit_atr = float(request.form.get("take_profit_atr", 3.0))
    market_filter = request.form.get("market_filter") == "on"
    signal_confirmation = request.form.get("signal_confirmation") == "on"
    emerging_only = request.form.get("emerging_only") == "on"
    trailing_stop = request.form.get("trailing_stop") == "on"
    max_hold_days = int(request.form.get("max_hold_days", 20))
    strategy_mode = request.form.get("strategy_mode") == "on"
    vpa_confirm = request.form.get("vpa_confirm") == "on"

    symbol_names = {s: get_symbol_name(s) for s in scan["stock_data"]}

    result = run_backtest(
        stock_data=scan["stock_data"],
        symbol_names=symbol_names,
        lookback_days=lookback,
        top_n=top_n,
        scan_interval=scan_interval,
        stop_loss_pct=stop_loss,
        min_price=min_price,
        max_price=max_price,
        trailing_stop=trailing_stop,
        signal_filter=signal_filter,
        capital=capital,
        volume_confirm=volume_confirm,
        trend_confirm=trend_confirm,
        take_profit_atr=take_profit_atr,
        market_filter=market_filter,
        signal_confirmation=signal_confirmation,
        emerging_only=emerging_only,
        max_hold_days=max_hold_days,
        strategy_mode=strategy_mode,
        vpa_confirm=vpa_confirm,
    )

    return _render("backtest.html", request, has_data=True, result=result)


@app.route("/watchlist")
def watchlist():
    """Watchlist with price alerts."""
    stocks = get_watchlist()

    items = []
    for stock in stocks:
        symbol = stock["symbol"]
        df = fetch_stock_data(symbol, period="5d")
        current = None
        change = None
        alert = None

        if df is not None and len(df) >= 2:
            current = df["Close"].iloc[-1]
            prev = df["Close"].iloc[-2]
            change = ((current - prev) / prev) * 100

            if stock["target_high"] > 0 and current >= stock["target_high"]:
                alert = "above"
            elif stock["target_low"] > 0 and current <= stock["target_low"]:
                alert = "below"

        items.append({
            **stock,
            "name": get_symbol_name(symbol),
            "current": current,
            "change": change,
            "alert": alert,
        })

    return _render("watchlist.html", request, items=items)


@app.route("/watchlist/quick-add", methods=["POST"])
def watchlist_quick_add():
    """Quick-add stock to watchlist from scanner (returns inline snippet)."""
    symbol = request.form.get("symbol", "").upper()
    if not symbol.endswith(".KL"):
        symbol += ".KL"
    if symbol in SYMBOLS:
        add_to_watchlist(symbol)
        return '<span class="text-green-400" title="Added to watchlist">✅</span>'
    return '<span class="text-red-400" title="Invalid symbol">❌</span>'


@app.route("/watchlist/add", methods=["POST"])
def watchlist_add():
    """Add stock to watchlist."""
    symbol = request.form.get("symbol", "").upper()
    if not symbol.endswith(".KL"):
        symbol += ".KL"
    target_high = float(request.form.get("target_high", 0) or 0)
    target_low = float(request.form.get("target_low", 0) or 0)
    notes = request.form.get("notes", "")

    if symbol in SYMBOLS:
        add_to_watchlist(symbol, target_high, target_low, notes)

    return watchlist()


@app.route("/watchlist/remove", methods=["POST"])
def watchlist_remove():
    """Remove stock from watchlist."""
    symbol = request.form.get("symbol", "")
    remove_from_watchlist(symbol)
    return watchlist()


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
    print("\n🎯 Stock Hunter Web — http://localhost:5001\n")
    app.run(debug=True, port=5001)
