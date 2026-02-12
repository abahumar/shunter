"""
Telegram notification module for Stock Hunter.
Sends scan results and sell alerts to Telegram.
"""

import os
import requests
from typing import Optional


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_message(text: str, token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    """Send a message via Telegram bot."""
    token = token or TELEGRAM_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("⚠ Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Split long messages (Telegram limit: 4096 chars)
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]

    for chunk in chunks:
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                print(f"⚠ Telegram error: {resp.text}")
                return False
        except Exception as e:
            print(f"⚠ Telegram send failed: {e}")
            return False

    return True


def format_scan_results(results: list, shariah: bool = False) -> str:
    """Format scan results as a Telegram message."""
    if not results:
        return "📊 <b>Stock Hunter Scan</b>\n\nNo BUY signals found today."

    label = "☪ Shariah" if shariah else "All"
    header = f"🎯 <b>Stock Hunter - {label} Scan</b>\n"
    header += f"📊 Found <b>{len(results)}</b> BUY signals\n\n"

    lines = []
    for i, r in enumerate(results[:15], 1):
        signal = r["signal"]
        emoji = "🟢" if "STRONG" in signal else "🔵"
        reasons = r.get("buy_reasons", [])
        reason_text = reasons[0] if reasons else ""
        lines.append(
            f"{emoji} <b>#{i} {r['symbol']}</b> — {r.get('name', '')}\n"
            f"   RM {r['close']:.2f} | Score: {r['net_score']} | {signal}\n"
            f"   <i>{reason_text}</i>\n"
        )

    footer = "\n💡 Run <code>python3 stock_hunter.py check SYMBOL</code> for details"
    return header + "\n".join(lines) + footer


def format_sell_alerts(alerts: list) -> str:
    """Format sell alerts as a Telegram message."""
    if not alerts:
        return ""

    header = "🔴 <b>SELL ALERTS</b>\n\n"
    lines = []
    for a in alerts:
        reasons = "; ".join(a.get("sell_reasons", [])[:2])
        pnl = a.get("pnl_pct", 0)
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        lines.append(
            f"⚠️ <b>{a['symbol']}</b> — {a.get('name', '')}\n"
            f"   {pnl_emoji} P/L: {pnl:+.1f}% | {a.get('signal', 'SELL')}\n"
            f"   <i>{reasons}</i>\n"
        )

    return header + "\n".join(lines)


def format_portfolio_summary(stocks: list) -> str:
    """Format portfolio status as a Telegram message."""
    if not stocks:
        return ""

    header = "📋 <b>Portfolio Status</b>\n\n"
    lines = []
    for s in stocks:
        pnl = s.get("pnl_pct", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        lines.append(
            f"{emoji} <b>{s['symbol']}</b> RM {s.get('current', 0):.2f} ({pnl:+.1f}%) — {s.get('signal', 'HOLD')}"
        )

    return header + "\n".join(lines)
