"""
Advanced signal features:
- Multi-timeframe confirmation (weekly + daily)
- Support/Resistance levels
- Volume spike detection
- Dividend yield scoring
- Risk sizing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

from scanner.indicators import compute_indicators, get_latest_indicators


def multi_timeframe_score(df_daily: pd.DataFrame) -> Tuple[int, str]:
    """
    Check if weekly and daily timeframes agree.
    Simulates weekly chart by resampling daily data.
    Returns (bonus_score, description).
    """
    if len(df_daily) < 50:
        return 0, ""

    # Resample to weekly
    df_weekly = df_daily.resample("W").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()

    if len(df_weekly) < 30:
        return 0, ""

    try:
        df_weekly = compute_indicators(df_weekly)
        weekly_ind = get_latest_indicators(df_weekly)

        df_daily_ind = compute_indicators(df_daily.copy())
        daily_ind = get_latest_indicators(df_daily_ind)
    except Exception:
        return 0, ""

    daily_bullish = (
        daily_ind.get("close", 0) > daily_ind.get("ema_50", 0)
        and daily_ind.get("macd_hist", 0) > 0
    )
    weekly_bullish = (
        weekly_ind.get("close", 0) > weekly_ind.get("ema_50", 0)
        and weekly_ind.get("macd_hist", 0) > 0
    )

    daily_bearish = (
        daily_ind.get("close", 0) < daily_ind.get("ema_50", 0)
        and daily_ind.get("macd_hist", 0) < 0
    )
    weekly_bearish = (
        weekly_ind.get("close", 0) < weekly_ind.get("ema_50", 0)
        and weekly_ind.get("macd_hist", 0) < 0
    )

    if daily_bullish and weekly_bullish:
        return 15, "Weekly + Daily both bullish ✅"
    elif daily_bearish and weekly_bearish:
        return -15, "Weekly + Daily both bearish ⛔"
    elif weekly_bullish and not daily_bullish:
        return 5, "Weekly bullish, daily pullback (dip buy?)"
    elif weekly_bearish and daily_bullish:
        return -5, "Daily bounce in weekly downtrend ⚠️"
    return 0, "Mixed signals"


def find_support_resistance(df: pd.DataFrame, levels: int = 3) -> Dict[str, list]:
    """
    Find key support and resistance levels using pivot points and price clusters.
    Returns dict with 'support' and 'resistance' price lists.
    """
    if len(df) < 50:
        return {"support": [], "resistance": []}

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    current = close[-1]

    # Find local highs and lows (pivot points)
    pivots_high = []
    pivots_low = []
    window = 10

    for i in range(window, len(df) - window):
        if high[i] == max(high[i - window:i + window + 1]):
            pivots_high.append(high[i])
        if low[i] == min(low[i - window:i + window + 1]):
            pivots_low.append(low[i])

    # Cluster nearby levels (within 2% of each other)
    def cluster_levels(prices, threshold=0.02):
        if not prices:
            return []
        prices = sorted(prices)
        clusters = []
        current_cluster = [prices[0]]
        for p in prices[1:]:
            if (p - current_cluster[0]) / current_cluster[0] < threshold:
                current_cluster.append(p)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [p]
        clusters.append(np.mean(current_cluster))
        return clusters

    all_resistance = cluster_levels([p for p in pivots_high if p > current])
    all_support = cluster_levels([p for p in pivots_low if p < current])

    # Return closest levels
    resistance = sorted(all_resistance)[:levels]
    support = sorted(all_support, reverse=True)[:levels]

    return {"support": support, "resistance": resistance}


def detect_volume_spike(df: pd.DataFrame, threshold: float = 2.5) -> Optional[dict]:
    """
    Detect unusual volume spikes (potential institutional activity).
    Returns spike info if detected, else None.
    """
    if len(df) < 25:
        return None

    vol = df["Volume"].values
    current_vol = vol[-1]
    avg_vol = np.mean(vol[-21:-1])  # 20-day avg excluding today

    if avg_vol <= 0:
        return None

    ratio = current_vol / avg_vol

    if ratio >= threshold:
        price_change = ((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100
        return {
            "volume_ratio": ratio,
            "avg_volume": avg_vol,
            "current_volume": current_vol,
            "price_change": price_change,
            "type": "Bullish spike 🟢" if price_change > 0 else "Bearish spike 🔴",
        }
    return None


def get_dividend_yield(info: dict) -> Optional[float]:
    """Extract dividend yield from stock info."""
    return info.get("dividendYield") or info.get("trailingAnnualDividendYield")


def calculate_position_size(
    capital: float,
    price: float,
    stop_loss_pct: float = -10.0,
    max_risk_pct: float = 2.0,
    max_allocation_pct: float = 15.0,
) -> dict:
    """
    Calculate position size based on risk management.

    Args:
        capital: total trading capital (e.g., RM 10,000)
        price: current stock price
        stop_loss_pct: stop-loss % (e.g., -10.0)
        max_risk_pct: max % of capital to risk per trade (e.g., 2%)
        max_allocation_pct: max % of capital in one stock (e.g., 15%)

    Returns:
        dict with lots, shares, amount, risk info
    """
    # Max amount by allocation limit
    max_amount = capital * (max_allocation_pct / 100)

    # Max amount by risk limit
    risk_amount = capital * (max_risk_pct / 100)
    loss_per_share = price * abs(stop_loss_pct) / 100
    if loss_per_share > 0:
        max_shares_by_risk = risk_amount / loss_per_share
    else:
        max_shares_by_risk = float("inf")

    max_shares_by_alloc = max_amount / price if price > 0 else 0

    # Take the smaller of the two
    shares = min(max_shares_by_risk, max_shares_by_alloc)

    # Round down to nearest lot (100 shares in Bursa Malaysia)
    lots = int(shares // 100)
    final_shares = lots * 100
    amount = final_shares * price
    risk = amount * abs(stop_loss_pct) / 100

    return {
        "lots": lots,
        "shares": final_shares,
        "amount": amount,
        "risk_amount": risk,
        "pct_of_capital": (amount / capital) * 100 if capital > 0 else 0,
        "price": price,
    }


def compute_risk_score(indicators: dict) -> dict:
    """
    Compute a risk level for a stock entry based on current indicators.
    Returns dict with risk_level (Low/Medium/High), risk_points, and warnings.
    Higher points = more risk.
    """
    points = 0
    warnings = []

    close = indicators.get("close", 0)
    atr = indicators.get("atr", 0)
    rsi = indicators.get("rsi", 50)
    adx = indicators.get("adx", 20)
    volume = indicators.get("volume", 0)
    vol_sma = indicators.get("volume_sma_20", 1)
    high_52w = indicators.get("high_52w", 0)
    low_52w = indicators.get("low_52w", 0)

    # ATR volatility (ATR as % of price)
    if close > 0 and atr > 0:
        atr_pct = (atr / close) * 100
        if atr_pct > 5:
            points += 3
            warnings.append("High volatility (ATR >5%)")
        elif atr_pct > 3:
            points += 1

    # RSI extremes
    if rsi and rsi > 75:
        points += 3
        warnings.append("Overbought (RSI >75)")
    elif rsi and rsi > 70:
        points += 1
    elif rsi and rsi < 25:
        points += 2
        warnings.append("Deeply oversold (RSI <25)")

    # Weak trend
    if adx and adx < 15:
        points += 2
        warnings.append("No clear trend (ADX <15)")

    # Low liquidity
    vol_ratio = volume / vol_sma if vol_sma and vol_sma > 0 else 1
    if vol_ratio < 0.5:
        points += 2
        warnings.append("Low volume (<0.5x avg)")

    # Near 52-week high
    if high_52w and low_52w and high_52w > low_52w and close > 0:
        position_52w = (close - low_52w) / (high_52w - low_52w) * 100
        if position_52w > 95:
            points += 3
            warnings.append("At 52-week high (>95%)")
        elif position_52w > 90:
            points += 1
            warnings.append("Near 52-week high (>90%)")

    # Classify
    if points >= 5:
        level = "High"
    elif points >= 2:
        level = "Medium"
    else:
        level = "Low"

    return {
        "level": level,
        "points": points,
        "warnings": warnings,
    }


def compute_confidence_grade(
    net_score: int,
    volume_ratio: float = 0,
    mtf_desc: str = "",
    risk_level: str = "Medium",
    confirmed: bool = False,
) -> dict:
    """
    Compute a single confidence grade (A-F) combining multiple factors.
    Helps users quickly assess signal quality at a glance.

    Returns dict with grade, label, color class, and breakdown.
    """
    points = 0
    factors = []

    # 1. Score strength (0-40 points)
    if net_score >= 70:
        points += 40
        factors.append("Very strong score")
    elif net_score >= 55:
        points += 30
        factors.append("Strong score")
    elif net_score >= 35:
        points += 20
        factors.append("Moderate score")
    elif net_score >= 10:
        points += 10
        factors.append("Weak score")
    else:
        factors.append("Poor score")

    # 2. Volume confirmation (0-20 points)
    if volume_ratio >= 2.0:
        points += 20
        factors.append("Strong volume")
    elif volume_ratio >= 1.5:
        points += 15
        factors.append("Good volume")
    elif volume_ratio >= 1.0:
        points += 8
        factors.append("Average volume")
    else:
        factors.append("Weak volume")

    # 3. Multi-timeframe alignment (0-20 points)
    if "both bullish" in mtf_desc.lower():
        points += 20
        factors.append("MTF aligned")
    elif "dip buy" in mtf_desc.lower():
        points += 10
        factors.append("Weekly bullish")
    elif "both bearish" in mtf_desc.lower():
        factors.append("MTF bearish")
    elif "downtrend" in mtf_desc.lower():
        factors.append("Weekly downtrend")
    else:
        points += 5

    # 4. Risk level (0-10 points)
    if risk_level == "Low":
        points += 10
        factors.append("Low risk")
    elif risk_level == "Medium":
        points += 5
    else:
        factors.append("High risk")

    # 5. Consecutive confirmation bonus (0-10 points)
    if confirmed:
        points += 10
        factors.append("Confirmed")

    # Grade classification (100-point scale)
    if points >= 75:
        grade, label = "A", "High Confidence"
    elif points >= 55:
        grade, label = "B", "Good"
    elif points >= 35:
        grade, label = "C", "Moderate"
    elif points >= 20:
        grade, label = "D", "Weak"
    else:
        grade, label = "F", "Avoid"

    return {
        "grade": grade,
        "label": label,
        "points": points,
        "factors": factors,
    }


def calculate_entry_plan(close: float, atr: float, atr_multiplier: float = 2.0) -> Optional[dict]:
    """
    Calculate dynamic stop-loss and take-profit based on ATR.
    Standard: stop = 2×ATR below, target = 3×ATR above (1.5:1 R/R).
    """
    if not atr or atr <= 0 or not close or close <= 0:
        return None

    stop_loss = close - (atr_multiplier * atr)
    take_profit = close + (atr_multiplier * 1.5 * atr)
    risk_per_share = close - stop_loss
    reward_per_share = take_profit - close
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0

    return {
        "entry": close,
        "stop_loss": max(stop_loss, 0.005),  # min 0.5 sen
        "take_profit": take_profit,
        "risk_per_share": risk_per_share,
        "reward_per_share": reward_per_share,
        "rr_ratio": rr_ratio,
        "atr": atr,
        "stop_pct": (risk_per_share / close) * 100 if close > 0 else 0,
        "target_pct": (reward_per_share / close) * 100 if close > 0 else 0,
    }
