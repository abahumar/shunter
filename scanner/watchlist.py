"""
Watchlist with price target alerts.
Stores watched stocks with optional target prices (upper/lower).
"""

import json
import os
from datetime import datetime

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "watchlist.json")


def _load_watchlist() -> dict:
    """Load watchlist from JSON file."""
    try:
        with open(WATCHLIST_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"stocks": []}


def _save_watchlist(data: dict):
    """Save watchlist to JSON file."""
    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    with open(WATCHLIST_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def add_to_watchlist(symbol: str, target_high: float = 0, target_low: float = 0, notes: str = ""):
    """Add or update a stock on the watchlist."""
    wl = _load_watchlist()

    for stock in wl["stocks"]:
        if stock["symbol"] == symbol:
            stock["target_high"] = target_high
            stock["target_low"] = target_low
            stock["notes"] = notes
            stock["updated_at"] = datetime.now().isoformat()
            _save_watchlist(wl)
            return

    wl["stocks"].append({
        "symbol": symbol,
        "target_high": target_high,
        "target_low": target_low,
        "notes": notes,
        "added_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    })
    _save_watchlist(wl)


def remove_from_watchlist(symbol: str) -> bool:
    """Remove a stock from the watchlist."""
    wl = _load_watchlist()
    original_len = len(wl["stocks"])
    wl["stocks"] = [s for s in wl["stocks"] if s["symbol"] != symbol]
    if len(wl["stocks"]) < original_len:
        _save_watchlist(wl)
        return True
    return False


def get_watchlist() -> list[dict]:
    """Get all stocks on the watchlist."""
    wl = _load_watchlist()
    return wl["stocks"]


def check_alerts(current_prices: dict) -> list[dict]:
    """
    Check watchlist against current prices.
    Returns list of triggered alerts.
    """
    alerts = []
    for stock in get_watchlist():
        symbol = stock["symbol"]
        price = current_prices.get(symbol)
        if price is None:
            continue

        if stock["target_high"] > 0 and price >= stock["target_high"]:
            alerts.append({
                "symbol": symbol,
                "type": "above",
                "target": stock["target_high"],
                "price": price,
            })
        if stock["target_low"] > 0 and price <= stock["target_low"]:
            alerts.append({
                "symbol": symbol,
                "type": "below",
                "target": stock["target_low"],
                "price": price,
            })
    return alerts
