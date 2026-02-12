"""
Portfolio tracker - stores bought stocks and checks for sell signals.
"""

import json
import os
from datetime import datetime

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.json")


def _load_portfolio() -> dict:
    """Load portfolio from JSON file."""
    try:
        with open(PORTFOLIO_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"stocks": []}


def _save_portfolio(data: dict):
    """Save portfolio to JSON file."""
    os.makedirs(os.path.dirname(PORTFOLIO_PATH), exist_ok=True)
    with open(PORTFOLIO_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def add_stock(symbol: str, buy_price: float, quantity: int = 0, notes: str = ""):
    """Add a stock to the portfolio."""
    portfolio = _load_portfolio()

    # Check if already exists
    for stock in portfolio["stocks"]:
        if stock["symbol"] == symbol:
            stock["buy_price"] = buy_price
            stock["quantity"] = quantity
            stock["notes"] = notes
            stock["updated_at"] = datetime.now().isoformat()
            _save_portfolio(portfolio)
            return

    portfolio["stocks"].append({
        "symbol": symbol,
        "buy_price": buy_price,
        "quantity": quantity,
        "notes": notes,
        "added_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    })
    _save_portfolio(portfolio)


def remove_stock(symbol: str) -> bool:
    """Remove a stock from the portfolio. Returns True if found and removed."""
    portfolio = _load_portfolio()
    original_len = len(portfolio["stocks"])
    portfolio["stocks"] = [s for s in portfolio["stocks"] if s["symbol"] != symbol]
    if len(portfolio["stocks"]) < original_len:
        _save_portfolio(portfolio)
        return True
    return False


def get_portfolio() -> list[dict]:
    """Get all stocks in the portfolio."""
    portfolio = _load_portfolio()
    return portfolio["stocks"]


def clear_portfolio():
    """Remove all stocks from portfolio."""
    _save_portfolio({"stocks": []})
