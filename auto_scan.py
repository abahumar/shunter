#!/usr/bin/env python3
"""
Automated scan script for scheduled runs (GitHub Actions / cron).
Scans Shariah-compliant stocks and sends results via Telegram.

Usage:
    python auto_scan.py                    # Scan + send Telegram
    python auto_scan.py --no-telegram      # Scan only, print to console
    python auto_scan.py --check-portfolio  # Also check portfolio sell alerts
"""

import argparse
import sys

from scanner.symbols import get_all_symbols, get_symbol_name, SYMBOLS
from scanner.data_fetcher import fetch_stock_data, fetch_bulk_data
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock
from scanner.portfolio import get_portfolio
from scanner.sectors import analyze_sectors
from scanner.advanced import multi_timeframe_score, detect_volume_spike
from scanner.signal_tracker import log_signals, update_outcomes, format_outcome_updates
from scanner.market_sentiment import fetch_market_sentiment
from scanner.telegram_notify import (
    send_message,
    format_scan_results,
    format_sell_alerts,
    format_portfolio_summary,
)


def run_scan(shariah: bool = True, min_price: float = 0.50, max_price: float = 3.00, top_n: int = 15):
    """Run full scan and return results."""
    symbols = get_all_symbols(shariah_only=shariah)
    data = fetch_bulk_data(symbols, period="1y", delay=0.2)

    results = []
    for symbol, df in data.items():
        try:
            df = compute_indicators(df)
            ind = get_latest_indicators(df)

            # Price filter
            close = ind.get("close", 0)
            if close < min_price:
                continue
            if max_price > 0 and close > max_price:
                continue

            analysis = analyze_stock(ind)
            if analysis["signal"] in ("STRONG BUY", "BUY"):
                # Multi-timeframe bonus and volume spike
                mtf_bonus, mtf_desc = multi_timeframe_score(df)
                analysis["net_score"] += mtf_bonus

                spike = detect_volume_spike(df)
                analysis["spike"] = f"{spike['volume_ratio']:.1f}x" if spike else ""

                analysis["symbol"] = symbol
                analysis["name"] = get_symbol_name(symbol)
                analysis["close"] = close
                results.append(analysis)
        except Exception:
            continue

    results.sort(key=lambda x: x["net_score"], reverse=True)
    return results[:top_n], data


def check_portfolio_alerts():
    """Check portfolio stocks for sell signals."""
    stocks = get_portfolio()
    if not stocks:
        return [], []

    alerts = []
    statuses = []

    for stock in stocks:
        symbol = stock["symbol"]
        buy_price = stock["buy_price"]

        df = fetch_stock_data(symbol, period="6mo")
        if df is None:
            continue

        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        analysis = analyze_stock(ind)

        current = ind["close"]
        pnl_pct = ((current - buy_price) / buy_price) * 100

        status = {
            "symbol": symbol,
            "name": get_symbol_name(symbol),
            "current": current,
            "buy_price": buy_price,
            "pnl_pct": pnl_pct,
            "signal": analysis["signal"],
        }
        statuses.append(status)

        if analysis["signal"] in ("SELL", "STRONG SELL"):
            status["sell_reasons"] = analysis["sell_reasons"]
            alerts.append(status)

    return alerts, statuses


def main():
    parser = argparse.ArgumentParser(description="Auto scan for scheduled runs")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram, print to console only")
    parser.add_argument("--check-portfolio", action="store_true", help="Also check portfolio for sell alerts")
    parser.add_argument("--shariah", action="store_true", default=True, help="Shariah-compliant only (default)")
    parser.add_argument("--min-price", type=float, default=0.50)
    parser.add_argument("--max-price", type=float, default=3.00)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    print("🎯 Stock Hunter Auto Scan")
    print("=" * 40)

    # 0. Check market sentiment
    print("\n📊 Checking market sentiment...")
    sentiment = fetch_market_sentiment()
    print(f"  Market: {sentiment['trend']} (score adj: {sentiment['score_adj']:+d})")
    for reason in sentiment.get("reasons", []):
        print(f"    • {reason}")

    # 1. Scan for BUY signals
    print("\n📊 Scanning stocks...")
    results, stock_data = run_scan(
        shariah=args.shariah,
        min_price=args.min_price,
        max_price=args.max_price,
        top_n=args.top,
    )
    print(f"✓ Found {len(results)} BUY signals")

    # Log signals for tracking
    logged = log_signals(results)
    if logged:
        print(f"📝 Logged {logged} new signals to tracker")

    # Check past signal outcomes
    outcome_updates = update_outcomes()
    if outcome_updates:
        print(f"📊 {len(outcome_updates)} signal outcomes updated")

    scan_msg = format_scan_results(results, shariah=args.shariah)

    # Add market sentiment to message
    sentiment_emoji = "🟢" if sentiment["trend"] == "Bullish" else ("🔴" if sentiment["trend"] == "Bearish" else "🟡")
    sentiment_msg = f"\n{sentiment_emoji} <b>Market: {sentiment['trend']}</b> ({sentiment['description']})\n"

    # 1b. Sector rotation summary
    sectors = analyze_sectors(stock_data)
    sector_msg = "\n\n<b>🔄 Sector Rotation</b>\n"
    for s in sectors[:5]:
        arrow = "🟢" if s["avg_pct_1m"] > 0 else "🔴"
        sector_msg += f"{arrow} <b>{s['sector']}</b>: {s['avg_pct_1m']:+.1f}% | {s['buy_signals']} buys\n"

    # 1c. Volume spikes
    spikes = []
    for symbol, df in stock_data.items():
        spike = detect_volume_spike(df)
        if spike:
            spikes.append(f"⚡ {symbol} ({spike['volume_ratio']:.1f}x, {spike['price_change']:+.1f}%)")
    spike_msg = ""
    if spikes:
        spike_msg = "\n\n<b>⚡ Volume Spikes</b>\n" + "\n".join(spikes[:10])

    # 2. Check portfolio (if requested)
    sell_msg = ""
    portfolio_msg = ""
    if args.check_portfolio:
        print("\n📋 Checking portfolio...")
        alerts, statuses = check_portfolio_alerts()
        if alerts:
            print(f"⚠ {len(alerts)} SELL alerts!")
            sell_msg = "\n\n" + format_sell_alerts(alerts)
        if statuses:
            portfolio_msg = "\n\n" + format_portfolio_summary(statuses)
        print(f"✓ Portfolio checked ({len(statuses)} stocks)")

    # 3. Send or print
    tracker_msg = format_outcome_updates(outcome_updates)
    full_msg = scan_msg + sentiment_msg + sector_msg + spike_msg + sell_msg + portfolio_msg + tracker_msg

    if args.no_telegram:
        # Strip HTML tags for console output
        import re
        clean = re.sub(r"<[^>]+>", "", full_msg)
        print("\n" + clean)
    else:
        print("\n📱 Sending to Telegram...")
        if send_message(full_msg):
            print("✓ Telegram message sent!")
        else:
            print("✗ Failed to send. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            # Still print to console as fallback
            import re
            clean = re.sub(r"<[^>]+>", "", full_msg)
            print("\n" + clean)
            sys.exit(1)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
