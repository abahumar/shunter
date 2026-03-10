"""
SQLite storage for portfolio, watchlist, and signal history.
Replaces JSON file storage for better concurrency and querying.
Automatically migrates existing JSON data on first run.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stockhunter.db")

# Legacy JSON paths for migration
_PORTFOLIO_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.json")
_WATCHLIST_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "watchlist.json")
_SIGNALS_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "signal_history.json")


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode for better concurrency."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist, then migrate JSON data."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio (
            symbol TEXT PRIMARY KEY,
            buy_price REAL NOT NULL,
            quantity INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            added_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            symbol TEXT PRIMARY KEY,
            target_high REAL DEFAULT 0,
            target_low REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            added_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT DEFAULT '',
            signal TEXT NOT NULL,
            score REAL DEFAULT 0,
            entry_price REAL NOT NULL,
            date TEXT NOT NULL,
            outcome_7d_price REAL,
            outcome_7d_pnl REAL,
            outcome_7d_date TEXT,
            outcome_14d_price REAL,
            outcome_14d_pnl REAL,
            outcome_14d_date TEXT,
            outcome_30d_price REAL,
            outcome_30d_pnl REAL,
            outcome_30d_date TEXT,
            UNIQUE(symbol, date)
        );
    """)
    conn.commit()
    _migrate_json(conn)
    conn.close()


def _migrate_json(conn: sqlite3.Connection):
    """Migrate existing JSON data to SQLite (one-time, idempotent)."""
    # Portfolio
    if os.path.exists(_PORTFOLIO_JSON):
        try:
            with open(_PORTFOLIO_JSON) as f:
                data = json.load(f)
            for s in data.get("stocks", []):
                conn.execute(
                    "INSERT OR IGNORE INTO portfolio (symbol, buy_price, quantity, notes, added_at, updated_at) VALUES (?,?,?,?,?,?)",
                    (s["symbol"], s["buy_price"], s.get("quantity", 0), s.get("notes", ""),
                     s.get("added_at", datetime.now().isoformat()), s.get("updated_at", datetime.now().isoformat()))
                )
            conn.commit()
            os.rename(_PORTFOLIO_JSON, _PORTFOLIO_JSON + ".migrated")
        except Exception:
            pass

    # Watchlist
    if os.path.exists(_WATCHLIST_JSON):
        try:
            with open(_WATCHLIST_JSON) as f:
                data = json.load(f)
            for s in data.get("stocks", []):
                conn.execute(
                    "INSERT OR IGNORE INTO watchlist (symbol, target_high, target_low, notes, added_at, updated_at) VALUES (?,?,?,?,?,?)",
                    (s["symbol"], s.get("target_high", 0), s.get("target_low", 0), s.get("notes", ""),
                     s.get("added_at", datetime.now().isoformat()), s.get("updated_at", datetime.now().isoformat()))
                )
            conn.commit()
            os.rename(_WATCHLIST_JSON, _WATCHLIST_JSON + ".migrated")
        except Exception:
            pass

    # Signal history
    if os.path.exists(_SIGNALS_JSON):
        try:
            with open(_SIGNALS_JSON) as f:
                data = json.load(f)
            for s in data.get("signals", []):
                outcomes = s.get("outcomes", {})
                conn.execute(
                    """INSERT OR IGNORE INTO signal_history
                       (symbol, name, signal, score, entry_price, date,
                        outcome_7d_price, outcome_7d_pnl, outcome_7d_date,
                        outcome_14d_price, outcome_14d_pnl, outcome_14d_date,
                        outcome_30d_price, outcome_30d_pnl, outcome_30d_date)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (s["symbol"], s.get("name", ""), s["signal"], s.get("score", 0),
                     s["entry_price"], s["date"],
                     outcomes.get("7d", {}).get("price"), outcomes.get("7d", {}).get("pnl_pct"), outcomes.get("7d", {}).get("date"),
                     outcomes.get("14d", {}).get("price"), outcomes.get("14d", {}).get("pnl_pct"), outcomes.get("14d", {}).get("date"),
                     outcomes.get("30d", {}).get("price"), outcomes.get("30d", {}).get("pnl_pct"), outcomes.get("30d", {}).get("date"))
                )
            conn.commit()
            os.rename(_SIGNALS_JSON, _SIGNALS_JSON + ".migrated")
        except Exception:
            pass


# ── Portfolio ──

def add_stock(symbol: str, buy_price: float, quantity: int = 0, notes: str = ""):
    """Add or update a stock in the portfolio."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO portfolio (symbol, buy_price, quantity, notes, added_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(symbol) DO UPDATE SET buy_price=?, quantity=?, notes=?, updated_at=?""",
        (symbol, buy_price, quantity, notes, now, now, buy_price, quantity, notes, now)
    )
    conn.commit()
    conn.close()


def remove_stock(symbol: str) -> bool:
    """Remove a stock from the portfolio."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_portfolio() -> List[dict]:
    """Get all stocks in the portfolio."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM portfolio ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_portfolio():
    """Remove all stocks from portfolio."""
    conn = _get_conn()
    conn.execute("DELETE FROM portfolio")
    conn.commit()
    conn.close()


# ── Watchlist ──

def add_to_watchlist(symbol: str, target_high: float = 0, target_low: float = 0, notes: str = ""):
    """Add or update a stock on the watchlist."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO watchlist (symbol, target_high, target_low, notes, added_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(symbol) DO UPDATE SET target_high=?, target_low=?, notes=?, updated_at=?""",
        (symbol, target_high, target_low, notes, now, now, target_high, target_low, notes, now)
    )
    conn.commit()
    conn.close()


def remove_from_watchlist(symbol: str) -> bool:
    """Remove a stock from the watchlist."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_watchlist() -> List[dict]:
    """Get all stocks on the watchlist."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_alerts(current_prices: dict) -> List[dict]:
    """Check watchlist against current prices for triggered alerts."""
    alerts = []
    for stock in get_watchlist():
        symbol = stock["symbol"]
        price = current_prices.get(symbol)
        if price is None:
            continue
        if stock["target_high"] > 0 and price >= stock["target_high"]:
            alerts.append({"symbol": symbol, "type": "above", "target": stock["target_high"], "price": price})
        if stock["target_low"] > 0 and price <= stock["target_low"]:
            alerts.append({"symbol": symbol, "type": "below", "target": stock["target_low"], "price": price})
    return alerts


# ── Signal History ──

def log_signals(results: list) -> int:
    """Log new BUY/STRONG BUY signals. Skips duplicates (same symbol+date)."""
    if not results:
        return 0
    conn = _get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    added = 0
    for r in results:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO signal_history (symbol, name, signal, score, entry_price, date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (r["symbol"], r.get("name", ""), r["signal"], r["net_score"], round(r["close"], 4), today)
            )
            added += conn.total_changes
        except Exception:
            pass
    conn.commit()
    conn.close()
    return added


def update_signal_outcome(symbol: str, date: str, period: str, price: float, pnl_pct: float, outcome_date: str):
    """Update outcome for a specific signal+period."""
    conn = _get_conn()
    col_price = f"outcome_{period}_price"
    col_pnl = f"outcome_{period}_pnl"
    col_date = f"outcome_{period}_date"
    conn.execute(
        f"UPDATE signal_history SET {col_price}=?, {col_pnl}=?, {col_date}=? WHERE symbol=? AND date=?",
        (price, pnl_pct, outcome_date, symbol, date)
    )
    conn.commit()
    conn.close()


def get_signals_needing_update(period: str) -> List[dict]:
    """Get signals that haven't had outcomes recorded for a given period."""
    conn = _get_conn()
    col = f"outcome_{period}_price"
    rows = conn.execute(
        f"SELECT * FROM signal_history WHERE {col} IS NULL ORDER BY date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_outcomes() -> int:
    """Check past signals and record 7/14/30-day outcomes. Returns count of updates."""
    from scanner.data_fetcher import fetch_stock_data

    today = datetime.now().date()
    updated = 0

    for days in [7, 14, 30]:
        key = f"{days}d"
        signals = get_signals_needing_update(key)

        for sig in signals:
            sig_date = datetime.strptime(sig["date"], "%Y-%m-%d").date()
            target_date = sig_date + timedelta(days=days)
            if today < target_date:
                continue

            price = _get_price_on_date(sig["symbol"], target_date)
            if price is not None:
                pnl_pct = round(((price - sig["entry_price"]) / sig["entry_price"]) * 100, 2)
                update_signal_outcome(
                    sig["symbol"], sig["date"], key,
                    round(price, 4), pnl_pct, target_date.strftime("%Y-%m-%d")
                )
                updated += 1

    return updated


def _get_price_on_date(symbol: str, target_date) -> Optional[float]:
    """Get the closing price for a symbol on or near a specific date."""
    from scanner.data_fetcher import fetch_stock_data

    try:
        df = fetch_stock_data(symbol, period="3mo")
        if df is None or df.empty:
            return None
        df.index = df.index.tz_localize(None) if df.index.tz else df.index

        # Find closest trading day on or after target
        mask = df.index.date >= target_date
        if mask.any():
            return float(df.loc[mask].iloc[0]["Close"])

        mask_before = df.index.date <= target_date
        if mask_before.any():
            return float(df.loc[mask_before].iloc[-1]["Close"])
    except Exception:
        pass
    return None


def get_tracker_stats() -> dict:
    """Compute signal tracker statistics from SQLite."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM signal_history").fetchone()[0]
    stats = {"total_signals": total}

    for days in [7, 14, 30]:
        key = f"{days}d"
        col_pnl = f"outcome_{days}d_pnl"
        rows = conn.execute(
            f"SELECT symbol, {col_pnl} as pnl FROM signal_history WHERE {col_pnl} IS NOT NULL"
        ).fetchall()

        if not rows:
            stats[key] = {"count": 0, "win_rate": 0, "avg_return": 0, "best": None, "worst": None}
            continue

        returns = [r["pnl"] for r in rows]
        wins = sum(1 for r in returns if r > 0)
        best_row = max(rows, key=lambda r: r["pnl"])
        worst_row = min(rows, key=lambda r: r["pnl"])

        stats[key] = {
            "count": len(rows),
            "win_rate": round((wins / len(rows)) * 100, 1),
            "avg_return": round(sum(returns) / len(returns), 2),
            "best": {"symbol": best_row["symbol"], "pnl": best_row["pnl"]},
            "worst": {"symbol": worst_row["symbol"], "pnl": worst_row["pnl"]},
        }

    conn.close()
    return stats


def get_recent_signals(n: int = 10) -> List[dict]:
    """Get N most recent signals with outcomes."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM signal_history ORDER BY date DESC, id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()

    # Convert to format compatible with existing templates
    result = []
    for r in rows:
        d = dict(r)
        outcomes = {}
        for days in [7, 14, 30]:
            key = f"{days}d"
            if d.get(f"outcome_{key}_price") is not None:
                outcomes[key] = {
                    "price": d[f"outcome_{key}_price"],
                    "pnl_pct": d[f"outcome_{key}_pnl"],
                    "date": d[f"outcome_{key}_date"],
                }
        d["outcomes"] = outcomes
        result.append(d)
    return result


def get_win_rate_by_score() -> List[dict]:
    """
    Compute win rates grouped by score ranges using 14-day outcomes.
    Returns list of dicts: [{range, label, count, wins, win_rate, avg_return}]
    """
    conn = _get_conn()
    rows = conn.execute(
        "SELECT score, outcome_14d_pnl FROM signal_history WHERE outcome_14d_pnl IS NOT NULL"
    ).fetchall()
    conn.close()

    buckets = [
        (60, 999, "60+", "Strong Buy Zone"),
        (35, 59, "35–59", "Buy Zone"),
        (10, 34, "10–34", "Watch Zone"),
    ]

    results = []
    for low, high, range_label, desc in buckets:
        matching = [r for r in rows if low <= (r["score"] or 0) <= high]
        count = len(matching)
        if count == 0:
            results.append({
                "range": range_label, "label": desc,
                "count": 0, "wins": 0, "win_rate": 0, "avg_return": 0,
            })
            continue

        returns = [r["outcome_14d_pnl"] for r in matching]
        wins = sum(1 for r in returns if r > 0)
        results.append({
            "range": range_label,
            "label": desc,
            "count": count,
            "wins": wins,
            "win_rate": round((wins / count) * 100, 1),
            "avg_return": round(sum(returns) / count, 2),
        })

    return results


# Initialize database on import
init_db()
