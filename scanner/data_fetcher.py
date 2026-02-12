"""
Fetch stock price data from Yahoo Finance for Bursa Malaysia stocks.
"""

import time
from typing import Dict, List, Optional

import yfinance as yf
import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn


def fetch_stock_data(symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Download OHLCV data for a single stock.
    Returns DataFrame with columns: Open, High, Low, Close, Volume
    Returns None if download fails.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, auto_adjust=True)
        if df.empty or len(df) < 50:
            return None
        return df
    except Exception:
        return None


def fetch_stock_info(symbol: str) -> dict:
    """Fetch basic info (P/E, market cap, sector) for a stock."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "pe_ratio": info.get("trailingPE"),
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector", "Unknown"),
            "name": info.get("shortName", symbol),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        }
    except Exception:
        return {}


def fetch_bulk_data(
    symbols: List[str],
    period: str = "1y",
    delay: float = 0.3,
) -> Dict[str, pd.DataFrame]:
    """
    Download data for multiple stocks with progress bar and rate limiting.
    Returns dict mapping symbol -> DataFrame.
    """
    results = {}
    failed = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
    ) as progress:
        task = progress.add_task("Scanning stocks...", total=len(symbols))

        for symbol in symbols:
            df = fetch_stock_data(symbol, period)
            if df is not None:
                results[symbol] = df
            else:
                failed.append(symbol)

            progress.advance(task)
            time.sleep(delay)

    if failed:
        print(f"  ⚠ Skipped {len(failed)} stocks (no data / delisted)")

    return results
