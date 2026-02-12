#!/usr/bin/env python3
"""
Stock Hunter Telegram Bot 🤖
Interactive bot that responds to commands from Telegram.

Commands:
    /scan          - Scan for BUY signals (Shariah, RM 0.50-3.00)
    /check <code>  - Check a specific stock (e.g., /check 5225)
    /sector        - Show sector rotation
    /spike         - Detect volume spikes
    /portfolio     - Check portfolio sell alerts
    /help          - Show available commands

Usage:
    # Set env vars first:
    export TELEGRAM_BOT_TOKEN="your_token"
    export TELEGRAM_CHAT_ID="your_chat_id"

    python bot.py                   # Run with long polling
    python bot.py --once            # Check once and exit (for cron/Actions)
"""

import os
import sys
import time
import json
import argparse
import requests
from typing import Optional

from scanner.symbols import get_all_symbols, get_symbol_name, search_symbol, is_shariah
from scanner.data_fetcher import fetch_stock_data, fetch_bulk_data
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock
from scanner.portfolio import get_portfolio
from scanner.sectors import analyze_sectors, get_sector
from scanner.advanced import (
    multi_timeframe_score,
    find_support_resistance,
    detect_volume_spike,
    calculate_position_size,
)
from scanner.telegram_notify import send_message

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
OFFSET_FILE = os.path.join(os.path.dirname(__file__), "data", ".bot_offset")


def get_updates(offset: Optional[int] = None, timeout: int = 30) -> list:
    """Fetch new messages from Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    try:
        resp = requests.get(url, params=params, timeout=timeout + 5)
        data = resp.json()
        return data.get("result", [])
    except Exception as e:
        print(f"⚠ getUpdates error: {e}")
        return []


def load_offset() -> Optional[int]:
    try:
        with open(OFFSET_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return None


def save_offset(offset: int):
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def reply(chat_id, text: str):
    """Send reply to a specific chat."""
    send_message(text, token=TOKEN, chat_id=str(chat_id))


# ──────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────

def handle_scan(chat_id):
    """Run a quick BUY signal scan."""
    reply(chat_id, "🔍 <b>Scanning Shariah stocks...</b>\nThis takes 1-2 minutes ⏳")

    symbols = get_all_symbols(shariah_only=True)
    data = fetch_bulk_data(symbols, period="1y", delay=0.2)

    results = []
    for symbol, df in data.items():
        try:
            df = compute_indicators(df)
            ind = get_latest_indicators(df)
            close = ind.get("close", 0)
            if close < 0.50 or close > 3.00:
                continue

            analysis = analyze_stock(ind)
            mtf_bonus, _ = multi_timeframe_score(df)
            analysis["net_score"] += mtf_bonus

            if analysis["signal"] in ("STRONG BUY", "BUY"):
                spike = detect_volume_spike(df)
                spike_txt = f" ⚡{spike['volume_ratio']:.1f}x" if spike else ""
                analysis["symbol"] = symbol
                analysis["name"] = get_symbol_name(symbol)
                analysis["close"] = close
                analysis["spike_txt"] = spike_txt
                results.append(analysis)
        except Exception:
            continue

    results.sort(key=lambda x: x["net_score"], reverse=True)

    if not results:
        reply(chat_id, "📊 No BUY signals found today.")
        return

    msg = f"🎯 <b>Stock Hunter Scan</b> (☪ Shariah)\n"
    msg += f"Found <b>{len(results)}</b> BUY signals\n\n"

    for i, r in enumerate(results[:15], 1):
        emoji = "🟢" if "STRONG" in r["signal"] else "🔵"
        reason = r.get("buy_reasons", [""])[0]
        msg += (
            f"{emoji} <b>#{i} {r['symbol']}</b> — {r['name']}\n"
            f"   RM {r['close']:.2f} | Score: {r['net_score']} | {r['signal']}{r['spike_txt']}\n"
            f"   <i>{reason}</i>\n\n"
        )

    msg += "💡 Use /check CODE for details"
    reply(chat_id, msg)


def handle_check(chat_id, args: str):
    """Check a specific stock in detail."""
    symbol = args.strip().upper()
    if not symbol:
        reply(chat_id, "❓ Usage: /check 5225\nPlease provide a stock code.")
        return

    if not symbol.endswith(".KL"):
        symbol += ".KL"

    name = get_symbol_name(symbol)
    if not name:
        reply(chat_id, f"❌ Stock <b>{symbol}</b> not found.\nTry /check 5225 or /check MAYBANK")
        return

    reply(chat_id, f"🔍 Analyzing <b>{symbol}</b>...")

    df = fetch_stock_data(symbol, period="1y")
    if df is None or len(df) < 50:
        reply(chat_id, f"❌ Not enough data for {symbol}")
        return

    df = compute_indicators(df)
    ind = get_latest_indicators(df)
    analysis = analyze_stock(ind)

    # Multi-timeframe
    mtf_bonus, mtf_desc = multi_timeframe_score(df)
    total_score = analysis["net_score"] + mtf_bonus

    # Support/Resistance
    sr = find_support_resistance(df)

    # Volume spike
    spike = detect_volume_spike(df)

    # Position sizing
    sizing = calculate_position_size(10000, ind["close"])

    # Sector
    sector = get_sector(symbol)
    shariah_label = "☪ Shariah" if is_shariah(symbol) else "Non-Shariah"

    # Build message
    signal = analysis["signal"]
    if signal in ("STRONG BUY", "BUY"):
        sig_emoji = "🟢"
    elif signal in ("SELL", "STRONG SELL"):
        sig_emoji = "🔴"
    else:
        sig_emoji = "🟡"

    msg = f"{sig_emoji} <b>{symbol} — {name}</b>\n"
    msg += f"Price: <b>RM {ind['close']:.2f}</b> | {signal} (Score: {total_score})\n"
    msg += f"Sector: {sector} | {shariah_label}\n\n"

    # Indicators
    msg += "<b>📊 Indicators</b>\n"
    msg += f"  RSI: {ind.get('rsi', 0):.0f} | ADX: {ind.get('adx', 0):.0f}\n"
    msg += f"  EMA20: {ind.get('ema_20', 0):.3f} | EMA50: {ind.get('ema_50', 0):.3f}\n"
    msg += f"  EMA200: {ind.get('ema_200', 0):.3f}\n"

    # Reasons
    if analysis["buy_reasons"]:
        msg += "\n<b>✅ Bullish</b>\n"
        for r in analysis["buy_reasons"][:4]:
            msg += f"  • {r}\n"
    if analysis["sell_reasons"]:
        msg += "\n<b>⛔ Bearish</b>\n"
        for r in analysis["sell_reasons"][:4]:
            msg += f"  • {r}\n"

    # Multi-timeframe
    if mtf_desc:
        msg += f"\n<b>📊 Multi-TF:</b> {mtf_desc} ({mtf_bonus:+d})\n"

    # S/R
    if sr["resistance"]:
        msg += "\n<b>📐 Resistance:</b> " + " → ".join(f"RM {r:.3f}" for r in sr["resistance"]) + "\n"
    if sr["support"]:
        msg += "<b>📐 Support:</b> " + " → ".join(f"RM {s:.3f}" for s in sr["support"]) + "\n"

    # Volume spike
    if spike:
        msg += f"\n⚡ <b>Volume Spike:</b> {spike['volume_ratio']:.1f}x avg ({spike['price_change']:+.1f}%)\n"

    # Sizing
    if sizing["lots"] > 0:
        msg += (
            f"\n💰 <b>Position Size</b> (RM 10k capital):\n"
            f"  Buy {sizing['lots']} lots ({sizing['shares']} shares) = RM {sizing['amount']:,.0f}\n"
        )

    reply(chat_id, msg)


def handle_sector(chat_id):
    """Show sector rotation."""
    reply(chat_id, "🔄 <b>Analyzing sector rotation...</b> ⏳")

    symbols = get_all_symbols(shariah_only=True)
    data = fetch_bulk_data(symbols, period="1y", delay=0.2)
    sectors = analyze_sectors(data)

    msg = "🔄 <b>Sector Rotation</b> (☪ Shariah)\n\n"
    for i, s in enumerate(sectors, 1):
        if s["avg_score"] >= 30:
            icon = "🟢"
        elif s["avg_score"] >= 10:
            icon = "🟡"
        elif s["avg_score"] >= -10:
            icon = "⚪"
        else:
            icon = "🔴"

        pct = s["avg_pct_1m"]
        top = s["top_stock"]
        msg += (
            f"{icon} <b>{s['sector']}</b>\n"
            f"   1M: {pct:+.1f}% | Score: {s['avg_score']:.0f} | "
            f"BUY: {s['buy_signals']} | SELL: {s['sell_signals']}\n"
            f"   Top: {top['symbol']} ({top['net_score']:+d})\n\n"
        )

    msg += "🟢 HOT  🟡 WARM  ⚪ NEUTRAL  🔴 COLD"
    reply(chat_id, msg)


def handle_spike(chat_id):
    """Detect volume spikes."""
    reply(chat_id, "⚡ <b>Scanning for volume spikes...</b> ⏳")

    symbols = get_all_symbols(shariah_only=True)
    data = fetch_bulk_data(symbols, period="3mo", delay=0.2)

    spikes = []
    for symbol, df in data.items():
        spike = detect_volume_spike(df, threshold=2.5)
        if spike:
            spike["symbol"] = symbol
            spike["name"] = get_symbol_name(symbol)
            spike["close"] = df["Close"].iloc[-1]
            spikes.append(spike)

    spikes.sort(key=lambda x: x["volume_ratio"], reverse=True)

    if not spikes:
        reply(chat_id, "⚡ No volume spikes detected today.")
        return

    msg = f"⚡ <b>Volume Spikes</b> (>2.5x avg)\n"
    msg += f"Found {len(spikes)} stocks\n\n"

    for s in spikes[:15]:
        pct_emoji = "🟢" if s["price_change"] > 0 else "🔴"
        msg += (
            f"{pct_emoji} <b>{s['symbol']}</b> — {s['name']}\n"
            f"   RM {s['close']:.2f} | {s['volume_ratio']:.1f}x vol | {s['price_change']:+.1f}%\n\n"
        )

    reply(chat_id, msg)


def handle_portfolio(chat_id):
    """Check portfolio for sell alerts."""
    stocks = get_portfolio()
    if not stocks:
        reply(chat_id, "📋 Portfolio is empty.\nAdd stocks via CLI: <code>python3 stock_hunter.py add 5225 8.50</code>")
        return

    reply(chat_id, f"📋 Checking {len(stocks)} portfolio stocks...")

    lines = []
    alerts = []
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
        pnl = ((current - buy_price) / buy_price) * 100
        emoji = "🟢" if pnl >= 0 else "🔴"

        lines.append(f"{emoji} <b>{symbol}</b> RM {current:.2f} ({pnl:+.1f}%) — {analysis['signal']}")

        if analysis["signal"] in ("SELL", "STRONG SELL"):
            reason = "; ".join(analysis["sell_reasons"][:2])
            alerts.append(f"⚠️ <b>{symbol}</b> — {analysis['signal']}\n   <i>{reason}</i>")

    msg = "📋 <b>Portfolio Status</b>\n\n" + "\n".join(lines)

    if alerts:
        msg += "\n\n🔴 <b>SELL ALERTS</b>\n\n" + "\n\n".join(alerts)

    reply(chat_id, msg)


def handle_help(chat_id):
    """Show help message."""
    msg = (
        "🎯 <b>Stock Hunter Bot</b>\n\n"
        "<b>Commands:</b>\n"
        "/scan — Scan for BUY signals (☪ Shariah, RM 0.50-3.00)\n"
        "/check CODE — Check a stock (e.g., /check 5225)\n"
        "/sector — Show sector rotation (hot/cold)\n"
        "/spike — Detect unusual volume spikes\n"
        "/portfolio — Check portfolio sell alerts\n"
        "/help — Show this message\n\n"
        "💡 <i>Scan takes 1-2 min to analyze 140+ stocks</i>"
    )
    reply(chat_id, msg)


# ──────────────────────────────────────────────
# Message router
# ──────────────────────────────────────────────

COMMANDS = {
    "/scan": lambda cid, _: handle_scan(cid),
    "/check": lambda cid, args: handle_check(cid, args),
    "/sector": lambda cid, _: handle_sector(cid),
    "/spike": lambda cid, _: handle_spike(cid),
    "/portfolio": lambda cid, _: handle_portfolio(cid),
    "/help": lambda cid, _: handle_help(cid),
    "/start": lambda cid, _: handle_help(cid),
}


def process_message(message: dict):
    """Route a Telegram message to the right handler."""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    # Parse command and arguments
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]  # handle /check@BotName format
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMANDS.get(cmd)
    if handler:
        print(f"📨 {cmd} {args}".strip())
        try:
            handler(chat_id, args)
        except Exception as e:
            print(f"⚠ Error handling {cmd}: {e}")
            reply(chat_id, f"❌ Error: {e}")
    elif text.startswith("/"):
        reply(chat_id, "❓ Unknown command. Use /help to see available commands.")


# ──────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────

def run_once():
    """Check for new messages once and process them."""
    offset = load_offset()
    updates = get_updates(offset=offset, timeout=0)

    if not updates:
        print("No new messages.")
        return

    for update in updates:
        msg = update.get("message")
        if msg:
            process_message(msg)
        save_offset(update["update_id"] + 1)

    print(f"Processed {len(updates)} updates.")


def run_polling():
    """Run long-polling loop (keeps running)."""
    print("🤖 Stock Hunter Bot started! Listening for commands...")
    print("   Press Ctrl+C to stop\n")

    offset = load_offset()

    while True:
        try:
            updates = get_updates(offset=offset, timeout=30)
            for update in updates:
                msg = update.get("message")
                if msg:
                    process_message(msg)
                offset = update["update_id"] + 1
                save_offset(offset)
        except KeyboardInterrupt:
            print("\n👋 Bot stopped.")
            break
        except Exception as e:
            print(f"⚠ Error: {e}")
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Stock Hunter Telegram Bot")
    parser.add_argument("--once", action="store_true", help="Check messages once and exit (for cron/Actions)")
    args = parser.parse_args()

    if not TOKEN:
        print("❌ Set TELEGRAM_BOT_TOKEN environment variable")
        print("   export TELEGRAM_BOT_TOKEN='your_token'")
        sys.exit(1)

    if args.once:
        run_once()
    else:
        run_polling()


if __name__ == "__main__":
    main()
