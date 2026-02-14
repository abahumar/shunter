"""
Signal tracker - auto-logs BUY signals and tracks profitability at 7, 14, and 30 days.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

from scanner.data_fetcher import fetch_stock_data

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "signal_history.json")

TRACK_DAYS = [7, 14, 30]


def _load_history() -> dict:
    try:
        with open(HISTORY_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"signals": []}


def _save_history(data: dict):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def log_signals(results: list):
    """Log new BUY/STRONG BUY signals. Skips duplicates (same symbol+date)."""
    if not results:
        return 0

    history = _load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    existing = {(s["symbol"], s["date"]) for s in history["signals"]}
    added = 0

    for r in results:
        key = (r["symbol"], today)
        if key in existing:
            continue
        history["signals"].append({
            "symbol": r["symbol"],
            "name": r.get("name", ""),
            "signal": r["signal"],
            "score": r["net_score"],
            "entry_price": round(r["close"], 4),
            "date": today,
            "outcomes": {},
        })
        existing.add(key)
        added += 1

    if added:
        _save_history(history)
    return added


def update_outcomes() -> list:
    """Check past signals that have reached 7/14/30 day marks and record outcomes.

    Returns list of newly completed outcomes for notification.
    """
    history = _load_history()
    today = datetime.now().date()
    updates = []
    changed = False

    for sig in history["signals"]:
        sig_date = datetime.strptime(sig["date"], "%Y-%m-%d").date()

        for days in TRACK_DAYS:
            key = f"{days}d"
            if key in sig["outcomes"]:
                continue

            target_date = sig_date + timedelta(days=days)
            if today < target_date:
                continue

            # Fetch price around the target date (use 5-day window)
            price = _get_price_on_date(sig["symbol"], target_date)
            if price is None:
                # If target date is a weekend/holiday, try next few trading days
                for offset in range(1, 5):
                    price = _get_price_on_date(sig["symbol"], target_date + timedelta(days=offset))
                    if price is not None:
                        break

            if price is not None:
                pnl_pct = round(((price - sig["entry_price"]) / sig["entry_price"]) * 100, 2)
                sig["outcomes"][key] = {
                    "price": round(price, 4),
                    "pnl_pct": pnl_pct,
                    "date": target_date.strftime("%Y-%m-%d"),
                }
                updates.append({
                    "symbol": sig["symbol"],
                    "name": sig["name"],
                    "signal": sig["signal"],
                    "entry_price": sig["entry_price"],
                    "period": key,
                    "exit_price": price,
                    "pnl_pct": pnl_pct,
                    "signal_date": sig["date"],
                })
                changed = True

    if changed:
        _save_history(history)
    return updates


def _get_price_on_date(symbol: str, target_date) -> Optional[float]:
    """Get the closing price for a symbol on or near a specific date."""
    try:
        start = target_date - timedelta(days=3)
        end = target_date + timedelta(days=3)
        df = fetch_stock_data(symbol, period="3mo")
        if df is None or df.empty:
            return None

        df.index = df.index.tz_localize(None) if df.index.tz else df.index

        # Find closest trading day on or after target
        mask = df.index.date >= target_date
        if mask.any():
            return float(df.loc[mask].iloc[0]["Close"])

        # Fallback: closest before target
        mask_before = df.index.date <= target_date
        if mask_before.any():
            return float(df.loc[mask_before].iloc[-1]["Close"])
    except Exception:
        pass
    return None


def get_tracker_stats() -> dict:
    """Compute overall signal tracker statistics."""
    history = _load_history()
    signals = history["signals"]

    stats = {"total_signals": len(signals)}

    for days in TRACK_DAYS:
        key = f"{days}d"
        completed = [s for s in signals if key in s["outcomes"]]
        if not completed:
            stats[key] = {"count": 0, "win_rate": 0, "avg_return": 0, "best": None, "worst": None}
            continue

        returns = [s["outcomes"][key]["pnl_pct"] for s in completed]
        wins = sum(1 for r in returns if r > 0)

        best = max(completed, key=lambda s: s["outcomes"][key]["pnl_pct"])
        worst = min(completed, key=lambda s: s["outcomes"][key]["pnl_pct"])

        stats[key] = {
            "count": len(completed),
            "win_rate": round((wins / len(completed)) * 100, 1),
            "avg_return": round(sum(returns) / len(returns), 2),
            "best": {"symbol": best["symbol"], "pnl": best["outcomes"][key]["pnl_pct"]},
            "worst": {"symbol": worst["symbol"], "pnl": worst["outcomes"][key]["pnl_pct"]},
        }

    return stats


def format_tracker_report() -> str:
    """Format signal tracker stats as a Telegram HTML message."""
    stats = get_tracker_stats()

    if stats["total_signals"] == 0:
        return "📈 <b>Signal Tracker</b>\n\nNo signals logged yet. Run a scan first!"

    msg = f"📈 <b>Signal Tracker</b>\n"
    msg += f"Total signals logged: <b>{stats['total_signals']}</b>\n\n"

    for days in TRACK_DAYS:
        key = f"{days}d"
        s = stats[key]
        if s["count"] == 0:
            msg += f"<b>📅 {days}-Day:</b> No data yet\n\n"
            continue

        win_emoji = "🟢" if s["win_rate"] >= 50 else "🔴"
        ret_emoji = "📈" if s["avg_return"] >= 0 else "📉"

        msg += f"<b>📅 {days}-Day Performance</b> ({s['count']} signals)\n"
        msg += f"  {win_emoji} Win Rate: <b>{s['win_rate']}%</b>\n"
        msg += f"  {ret_emoji} Avg Return: <b>{s['avg_return']:+.2f}%</b>\n"
        if s["best"]:
            msg += f"  🏆 Best: {s['best']['symbol']} ({s['best']['pnl']:+.2f}%)\n"
        if s["worst"]:
            msg += f"  💀 Worst: {s['worst']['symbol']} ({s['worst']['pnl']:+.2f}%)\n"
        msg += "\n"

    return msg


def format_outcome_updates(updates: list) -> str:
    """Format newly completed outcomes for Telegram notification."""
    if not updates:
        return ""

    msg = "\n\n📊 <b>Signal Tracker Updates</b>\n\n"
    for u in updates:
        emoji = "🟢" if u["pnl_pct"] >= 0 else "🔴"
        msg += (
            f"{emoji} <b>{u['symbol']}</b> — {u['name']}\n"
            f"   {u['period']}: RM {u['entry_price']:.2f} → RM {u['exit_price']:.2f} "
            f"(<b>{u['pnl_pct']:+.2f}%</b>)\n"
            f"   Signal: {u['signal']} on {u['signal_date']}\n\n"
        )

    return msg


def get_recent_signals(n: int = 10) -> list:
    """Get the N most recent signals with their outcomes."""
    history = _load_history()
    return list(reversed(history["signals"][-n:]))
