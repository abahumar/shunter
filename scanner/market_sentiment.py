"""
Market sentiment analysis using KLCI (FTSE Bursa Malaysia KLCI) index.
Determines if the overall market is bullish, bearish, or neutral.
Used to adjust individual stock scores — avoid buying in a bear market.
"""

from typing import Optional, Dict

import pandas as pd

from scanner.data_fetcher import fetch_stock_data
from scanner.indicators import compute_indicators, get_latest_indicators

KLCI_SYMBOL = "^KLSE"


def fetch_market_sentiment(klci_df: Optional[pd.DataFrame] = None) -> Dict:
    """
    Analyze KLCI index to determine overall market sentiment.

    Returns dict with:
        trend: "Bullish" / "Bearish" / "Neutral" / "Unknown"
        score_adj: int bonus/penalty to apply to individual stock scores
        description: human-readable explanation
        reasons: list of contributing factors
        details: dict with raw indicator values
    """
    if klci_df is None:
        klci_df = fetch_stock_data(KLCI_SYMBOL, period="1y")

    if klci_df is None or len(klci_df) < 50:
        return _unknown_sentiment("KLCI data unavailable")

    try:
        klci_df = compute_indicators(klci_df)
        ind = get_latest_indicators(klci_df)
    except Exception:
        return _unknown_sentiment("Failed to compute KLCI indicators")

    return _analyze_sentiment(ind)


def compute_sentiment_at(klci_df: pd.DataFrame, end_idx: int) -> Dict:
    """
    Compute market sentiment at a specific point in time (for backtesting).
    Uses data only up to end_idx to avoid look-ahead bias.
    """
    if klci_df is None or end_idx < 200 or end_idx >= len(klci_df):
        return _unknown_sentiment("")

    sliced = klci_df.iloc[:end_idx + 1].copy()
    try:
        sliced = compute_indicators(sliced)
        ind = get_latest_indicators(sliced)
    except Exception:
        return _unknown_sentiment("")

    return _analyze_sentiment(ind)


def _analyze_sentiment(ind: dict) -> Dict:
    """Core sentiment analysis from indicator values."""
    close = ind.get("close", 0)
    ema_50 = ind.get("ema_50", 0)
    ema_200 = ind.get("ema_200", 0)
    macd_hist = ind.get("macd_hist", 0)
    rsi = ind.get("rsi", 50)

    bullish_pts = 0
    bearish_pts = 0
    reasons = []

    # EMA trend (strongest weight)
    if close and ema_50 and ema_200:
        if close > ema_50 > ema_200:
            bullish_pts += 2
            reasons.append("KLCI uptrend (Price > EMA50 > EMA200)")
        elif close < ema_50 < ema_200:
            bearish_pts += 2
            reasons.append("KLCI downtrend (Price < EMA50 < EMA200)")
        elif close > ema_50:
            bullish_pts += 1
            reasons.append("KLCI above EMA50")
        elif close < ema_50:
            bearish_pts += 1
            reasons.append("KLCI below EMA50")

    # MACD momentum
    if macd_hist is not None:
        if macd_hist > 0:
            bullish_pts += 1
            reasons.append("KLCI MACD positive")
        elif macd_hist < 0:
            bearish_pts += 1
            reasons.append("KLCI MACD negative")

    # RSI
    if rsi is not None:
        if rsi > 55:
            bullish_pts += 1
            reasons.append(f"KLCI RSI {rsi:.0f} (bullish)")
        elif rsi < 45:
            bearish_pts += 1
            reasons.append(f"KLCI RSI {rsi:.0f} (bearish)")

    # Determine overall sentiment
    net = bullish_pts - bearish_pts
    if net >= 2:
        trend = "Bullish"
        score_adj = 5
        description = "Market bullish — favorable for buying"
    elif net <= -2:
        trend = "Bearish"
        score_adj = -10
        description = "Market bearish — higher risk for new buys"
    else:
        trend = "Neutral"
        score_adj = 0
        description = "Market neutral — mixed signals"

    return {
        "trend": trend,
        "score_adj": score_adj,
        "description": description,
        "reasons": reasons,
        "details": {
            "close": close,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "macd_hist": macd_hist,
            "rsi": rsi,
            "bullish_pts": bullish_pts,
            "bearish_pts": bearish_pts,
        },
    }


def _unknown_sentiment(description: str) -> Dict:
    """Return a neutral/unknown sentiment result."""
    return {
        "trend": "Unknown",
        "score_adj": 0,
        "description": description,
        "reasons": [],
        "details": {},
    }
