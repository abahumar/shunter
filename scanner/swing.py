"""
Swing trade setup detection for Bursa Malaysia stocks.

Identifies 6 classic swing setups with holding-period labels,
entry/exit levels, and strength scores.
"""

import math
from typing import List, Optional

import pandas as pd
import numpy as np


def detect_swing_setups(
    df: pd.DataFrame,
    indicators: dict,
    support_resistance: Optional[dict] = None,
) -> List[dict]:
    """
    Scan a single stock for swing trade setups.

    Returns a list of matched setups (may be empty). Each setup dict:
      type, holding, entry, stop_loss, target, rr_ratio, strength, reasons
    """
    if df is None or len(df) < 50:
        return []

    setups: List[dict] = []

    close = indicators.get("close", 0)
    atr = indicators.get("atr", 0)
    if not close or not atr:
        return []

    s = _check_ema_pullback(df, indicators, close, atr)
    if s:
        setups.append(s)

    s = _check_oversold_bounce(df, indicators, close, atr)
    if s:
        setups.append(s)

    s = _check_breakout(df, indicators, close, atr, support_resistance)
    if s:
        setups.append(s)

    s = _check_macd_crossover(df, indicators, close, atr)
    if s:
        setups.append(s)

    s = _check_bb_squeeze(df, indicators, close, atr)
    if s:
        setups.append(s)

    s = _check_support_bounce(df, indicators, close, atr, support_resistance)
    if s:
        setups.append(s)

    return setups


# ── Individual setup detectors ──────────────────────────────────────


def _check_ema_pullback(df, ind, close, atr) -> Optional[dict]:
    """
    EMA Pullback (3-5 days): Price in uptrend pulls back near EMA20/50,
    then shows signs of bouncing.
    """
    ema20 = ind.get("ema_20")
    ema50 = ind.get("ema_50")
    ema200 = ind.get("ema_200")
    rsi = ind.get("rsi", 50)
    volume = ind.get("volume", 0)
    vol_sma = ind.get("volume_sma_20", 1) or 1

    if not all([ema20, ema50, ema200]):
        return None

    # Must be in an uptrend: EMA20 > EMA50 > EMA200
    if not (ema20 > ema50 > ema200):
        return None

    reasons = []
    strength = 0

    # Price pulled back near EMA20 (within 1.5 × ATR)
    dist_ema20 = close - ema20
    near_ema20 = -0.5 * atr <= dist_ema20 <= 1.5 * atr

    # Price pulled back near EMA50 (within 1.5 × ATR)
    dist_ema50 = close - ema50
    near_ema50 = -0.5 * atr <= dist_ema50 <= 1.5 * atr

    if not (near_ema20 or near_ema50):
        return None

    if near_ema20:
        strength += 2
        reasons.append("Pullback to EMA20")
    if near_ema50:
        strength += 2
        reasons.append("Pullback to EMA50")

    # Bounce confirmation: today's close above yesterday's close
    if len(df) >= 2 and df["Close"].iloc[-1] > df["Close"].iloc[-2]:
        strength += 1
        reasons.append("Bounce confirmed (green candle)")

    # RSI not overbought
    if 35 <= rsi <= 60:
        strength += 1
        reasons.append(f"RSI {rsi:.0f} (healthy)")

    # Volume picking up
    vol_ratio = volume / vol_sma
    if vol_ratio > 1.2:
        strength += 1
        reasons.append(f"Volume rising ({vol_ratio:.1f}×)")

    if strength < 3:
        return None

    entry = round(close, 4)
    stop = round(close - 2 * atr, 4)
    target = round(close + 3 * atr, 4)
    rr = round((target - entry) / (entry - stop), 1) if entry > stop else 0

    return {
        "type": "EMA Pullback",
        "holding": "3–5 days",
        "entry": entry,
        "stop_loss": stop,
        "target": target,
        "rr_ratio": rr,
        "strength": min(strength, 5),
        "reasons": reasons,
    }


def _check_oversold_bounce(df, ind, close, atr) -> Optional[dict]:
    """
    Oversold Bounce (3-10 days): RSI was recently < 35 and is now recovering.
    Mean-reversion opportunity.
    """
    rsi = ind.get("rsi")
    stoch_k = ind.get("stoch_rsi_k")
    ema50 = ind.get("ema_50")
    volume = ind.get("volume", 0)
    vol_sma = ind.get("volume_sma_20", 1) or 1

    if rsi is None:
        return None

    # RSI was recently oversold (check last 5 bars)
    rsi_col = df.get("RSI")
    if rsi_col is None or len(rsi_col) < 5:
        return None

    recent_rsi = rsi_col.iloc[-5:]
    was_oversold = any(v < 35 for v in recent_rsi if not math.isnan(v))
    if not was_oversold:
        return None

    # RSI is now recovering (current > 30)
    if rsi < 30:
        return None  # still falling

    reasons = []
    strength = 0

    strength += 2
    reasons.append(f"RSI recovering from oversold ({rsi:.0f})")

    # RSI turning up
    if rsi > recent_rsi.iloc[-2]:
        strength += 1
        reasons.append("RSI turning upward")

    # Stochastic RSI confirmation
    if stoch_k is not None and stoch_k < 30:
        strength += 1
        reasons.append(f"StochRSI {stoch_k:.0f} (oversold)")

    # Price above EMA50 (not in a downtrend crash)
    if ema50 and close > ema50 * 0.95:
        strength += 1
        reasons.append("Price near/above EMA50 (not broken)")

    # Volume on recovery
    vol_ratio = volume / vol_sma
    if vol_ratio > 1.0:
        strength += 1
        reasons.append(f"Volume on recovery ({vol_ratio:.1f}×)")

    if strength < 3:
        return None

    entry = round(close, 4)
    stop = round(close - 2.5 * atr, 4)
    target = round(close + 3.5 * atr, 4)
    rr = round((target - entry) / (entry - stop), 1) if entry > stop else 0

    return {
        "type": "Oversold Bounce",
        "holding": "3–10 days",
        "entry": entry,
        "stop_loss": stop,
        "target": target,
        "rr_ratio": rr,
        "strength": min(strength, 5),
        "reasons": reasons,
    }


def _check_breakout(df, ind, close, atr, sr) -> Optional[dict]:
    """
    Breakout (1-2 weeks): Price breaks above a resistance level or
    recent consolidation high with volume surge.
    """
    volume = ind.get("volume", 0)
    vol_sma = ind.get("volume_sma_20", 1) or 1
    adx = ind.get("adx", 0)
    di_plus = ind.get("di_plus", 0)
    di_minus = ind.get("di_minus", 0)
    high_52w = ind.get("high_52w", 0)

    reasons = []
    strength = 0

    # Method 1: Breaking above recent 20-day high
    if len(df) >= 20:
        recent_high = df["High"].iloc[-21:-1].max()
        if close > recent_high:
            strength += 2
            reasons.append(f"Breaking 20-day high ({recent_high:.3f})")

    # Method 2: Breaking above S/R resistance level
    if sr and sr.get("resistance"):
        nearest_res = sr["resistance"][0]
        if close > nearest_res and close < nearest_res * 1.03:
            strength += 2
            reasons.append(f"Breaking resistance {nearest_res:.3f}")

    if strength < 2:
        return None

    # Volume confirmation (must have above-avg volume)
    vol_ratio = volume / vol_sma
    if vol_ratio >= 2.0:
        strength += 2
        reasons.append(f"Strong volume ({vol_ratio:.1f}×)")
    elif vol_ratio >= 1.5:
        strength += 1
        reasons.append(f"Good volume ({vol_ratio:.1f}×)")
    else:
        return None  # breakout without volume is suspect

    # ADX trending
    if adx and adx > 20 and di_plus and di_minus and di_plus > di_minus:
        strength += 1
        reasons.append(f"ADX {adx:.0f} bullish trend")

    # Near 52-week high adds conviction
    if high_52w and close > high_52w * 0.95:
        strength += 1
        reasons.append("Near 52-week high")

    if strength < 3:
        return None

    entry = round(close, 4)
    stop = round(close - 2 * atr, 4)
    target = round(close + 4 * atr, 4)
    rr = round((target - entry) / (entry - stop), 1) if entry > stop else 0

    return {
        "type": "Breakout",
        "holding": "1–2 weeks",
        "entry": entry,
        "stop_loss": stop,
        "target": target,
        "rr_ratio": rr,
        "strength": min(strength, 5),
        "reasons": reasons,
    }


def _check_macd_crossover(df, ind, close, atr) -> Optional[dict]:
    """
    MACD Bullish Crossover (1-2 weeks): MACD crosses above signal line,
    preferably from below zero.
    """
    macd = ind.get("macd")
    macd_signal = ind.get("macd_signal")
    macd_hist = ind.get("macd_hist")
    macd_hist_prev = ind.get("macd_hist_prev")
    ema20 = ind.get("ema_20")
    ema50 = ind.get("ema_50")
    rsi = ind.get("rsi", 50)

    if any(v is None for v in [macd, macd_signal, macd_hist, macd_hist_prev]):
        return None

    if any(math.isnan(v) for v in [macd, macd_signal, macd_hist, macd_hist_prev]):
        return None

    # MACD must have just crossed bullish (histogram flipped positive)
    if not (macd_hist_prev < 0 and macd_hist > 0):
        return None

    reasons = []
    strength = 2
    reasons.append("MACD bullish crossover")

    # Crossover from below zero is stronger
    if macd < 0:
        strength += 1
        reasons.append("Crossover below zero (early)")

    # EMA alignment supports
    if ema20 and ema50 and ema20 > ema50:
        strength += 1
        reasons.append("EMA20 > EMA50 (trend support)")

    # RSI confirms momentum
    if 40 <= rsi <= 65:
        strength += 1
        reasons.append(f"RSI {rsi:.0f} (momentum zone)")

    if strength < 3:
        return None

    entry = round(close, 4)
    stop = round(close - 2 * atr, 4)
    target = round(close + 3.5 * atr, 4)
    rr = round((target - entry) / (entry - stop), 1) if entry > stop else 0

    return {
        "type": "MACD Crossover",
        "holding": "1–2 weeks",
        "entry": entry,
        "stop_loss": stop,
        "target": target,
        "rr_ratio": rr,
        "strength": min(strength, 5),
        "reasons": reasons,
    }


def _check_bb_squeeze(df, ind, close, atr) -> Optional[dict]:
    """
    Bollinger Band Squeeze Breakout (1-4 weeks): Bands contracted tightly
    (low volatility), then price breaks above the upper band with volume.
    """
    bb_upper = ind.get("bb_upper")
    bb_lower = ind.get("bb_lower")
    bb_mid = ind.get("bb_mid")
    volume = ind.get("volume", 0)
    vol_sma = ind.get("volume_sma_20", 1) or 1

    if not all([bb_upper, bb_lower, bb_mid]):
        return None
    if any(math.isnan(v) for v in [bb_upper, bb_lower, bb_mid]):
        return None

    # Current bandwidth
    bandwidth = (bb_upper - bb_lower) / bb_mid if bb_mid > 0 else 0

    # Historical bandwidth (look for squeeze = narrow bands)
    if "BB_upper" not in df.columns or "BB_mid" not in df.columns:
        return None

    bw_series = (df["BB_upper"] - df["BB_lower"]) / df["BB_mid"]
    bw_series = bw_series.dropna()
    if len(bw_series) < 20:
        return None

    avg_bw = bw_series.iloc[-60:].mean() if len(bw_series) >= 60 else bw_series.mean()

    # Squeeze: current bandwidth < 70% of average
    is_squeeze = bandwidth < avg_bw * 0.70

    # Recent squeeze in last 5 bars
    recent_bw = bw_series.iloc[-5:]
    was_recent_squeeze = any(v < avg_bw * 0.70 for v in recent_bw)

    if not (is_squeeze or was_recent_squeeze):
        return None

    reasons = []
    strength = 0

    strength += 2
    reasons.append(f"BB squeeze detected (width {bandwidth:.3f} vs avg {avg_bw:.3f})")

    # Price breaking above upper band or mid band
    if close > bb_upper:
        strength += 2
        reasons.append("Price above upper BB (breakout)")
    elif close > bb_mid:
        strength += 1
        reasons.append("Price above BB midline")
    else:
        return None  # no breakout direction yet

    # Volume confirmation
    vol_ratio = volume / vol_sma
    if vol_ratio >= 1.5:
        strength += 1
        reasons.append(f"Volume expanding ({vol_ratio:.1f}×)")

    if strength < 3:
        return None

    entry = round(close, 4)
    stop = round(bb_mid, 4)
    target = round(close + (close - bb_mid) * 2, 4)
    rr = round((target - entry) / (entry - stop), 1) if entry > stop else 0

    return {
        "type": "BB Squeeze",
        "holding": "1–4 weeks",
        "entry": entry,
        "stop_loss": stop,
        "target": target,
        "rr_ratio": rr,
        "strength": min(strength, 5),
        "reasons": reasons,
    }


def _check_support_bounce(df, ind, close, atr, sr) -> Optional[dict]:
    """
    Support Bounce (1-2 weeks): Price tests a key support level and bounces
    with volume confirmation.
    """
    volume = ind.get("volume", 0)
    vol_sma = ind.get("volume_sma_20", 1) or 1
    rsi = ind.get("rsi", 50)
    low = ind.get("low", close)
    ema200 = ind.get("ema_200")
    bb_lower = ind.get("bb_lower")

    reasons = []
    strength = 0

    support_level = None

    # Check S/R support levels
    if sr and sr.get("support"):
        nearest_sup = sr["support"][0]
        dist = (close - nearest_sup) / nearest_sup if nearest_sup > 0 else 999
        if 0 <= dist <= 0.03:  # within 3% above support
            strength += 2
            support_level = nearest_sup
            reasons.append(f"Bouncing off support {nearest_sup:.3f}")

    # Check EMA200 as dynamic support
    if ema200 and not support_level:
        dist_ema200 = (close - ema200) / ema200
        if 0 <= dist_ema200 <= 0.02:
            strength += 2
            support_level = ema200
            reasons.append(f"Bouncing off EMA200 ({ema200:.3f})")

    # Check lower Bollinger Band as support
    if bb_lower and not support_level:
        if not math.isnan(bb_lower):
            dist_bb = (close - bb_lower) / bb_lower if bb_lower > 0 else 999
            if 0 <= dist_bb <= 0.02:
                strength += 1
                support_level = bb_lower
                reasons.append(f"Bouncing off lower BB ({bb_lower:.3f})")

    if not support_level:
        return None

    # Bounce confirmation: today close > yesterday close, low touched near support
    if len(df) >= 2:
        prev_close = df["Close"].iloc[-2]
        if close > prev_close:
            strength += 1
            reasons.append("Green candle confirmation")
        if low <= support_level * 1.01:
            strength += 1
            reasons.append("Wick tested support level")

    # RSI not deeply oversold (healthy bounce, not falling knife)
    if rsi and 30 <= rsi <= 55:
        strength += 1
        reasons.append(f"RSI {rsi:.0f} (supportive)")

    # Volume on bounce
    vol_ratio = volume / vol_sma
    if vol_ratio >= 1.2:
        strength += 1
        reasons.append(f"Volume on bounce ({vol_ratio:.1f}×)")

    if strength < 3:
        return None

    entry = round(close, 4)
    stop = round(support_level - 1.5 * atr, 4)
    target = round(close + 3 * atr, 4)
    rr = round((target - entry) / (entry - stop), 1) if entry > stop else 0

    return {
        "type": "Support Bounce",
        "holding": "1–2 weeks",
        "entry": entry,
        "stop_loss": stop,
        "target": target,
        "rr_ratio": rr,
        "strength": min(strength, 5),
        "reasons": reasons,
    }
