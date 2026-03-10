"""
Volume Price Analysis (VPA) — reads the story behind the candles.

Analyzes the relationship between volume, spread (candle range), and close
position to detect smart money accumulation/distribution patterns.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# ── Bar Classification Helpers ──────────────────────────────────────────

def _close_position(o: float, h: float, l: float, c: float) -> float:
    """Where did price close within the bar? 0.0 = bottom, 1.0 = top."""
    spread = h - l
    if spread == 0:
        return 0.5
    return (c - l) / spread


def _classify_spread(spread: float, avg_spread: float) -> str:
    """Classify bar spread relative to average."""
    if avg_spread == 0:
        return "average"
    ratio = spread / avg_spread
    if ratio >= 2.0:
        return "ultra_wide"
    if ratio >= 1.3:
        return "wide"
    if ratio <= 0.5:
        return "narrow"
    return "average"


def _classify_volume(volume: float, avg_volume: float) -> str:
    """Classify volume relative to 20-day average."""
    if avg_volume == 0:
        return "average"
    ratio = volume / avg_volume
    if ratio >= 2.5:
        return "ultra_high"
    if ratio >= 1.5:
        return "high"
    if ratio <= 0.6:
        return "low"
    return "average"


def _is_up_bar(o: float, c: float) -> bool:
    return c > o


def _is_down_bar(o: float, c: float) -> bool:
    return c < o


# ── VPA Pattern Detection ───────────────────────────────────────────────

def _detect_accumulation(bar: dict) -> Optional[dict]:
    """
    Accumulation: smart money buying quietly.
    High/ultra-high volume + close in upper third + any bar direction.
    """
    if bar["vol_class"] not in ("high", "ultra_high"):
        return None
    if bar["close_pos"] < 0.6:
        return None
    return {
        "pattern": "Accumulation",
        "bias": "bullish",
        "strength": 2 if bar["vol_class"] == "ultra_high" else 1,
        "desc": "High volume with close near top — smart money buying",
    }


def _detect_distribution(bar: dict) -> Optional[dict]:
    """
    Distribution: smart money selling into buying.
    High/ultra-high volume + close in lower third.
    """
    if bar["vol_class"] not in ("high", "ultra_high"):
        return None
    if bar["close_pos"] > 0.4:
        return None
    return {
        "pattern": "Distribution",
        "bias": "bearish",
        "strength": 2 if bar["vol_class"] == "ultra_high" else 1,
        "desc": "High volume with close near bottom — smart money selling",
    }


def _detect_buying_climax(bar: dict) -> Optional[dict]:
    """
    Buying Climax: frenzied buying about to exhaust.
    Ultra-high volume + wide/ultra-wide up bar + close in middle or lower half.
    """
    if bar["vol_class"] != "ultra_high":
        return None
    if bar["spread_class"] not in ("wide", "ultra_wide"):
        return None
    if not bar["is_up"]:
        return None
    if bar["close_pos"] > 0.5:
        return None
    return {
        "pattern": "Buying Climax",
        "bias": "bearish",
        "strength": 2,
        "desc": "Ultra-high volume up bar closing weak — buying exhaustion",
    }


def _detect_selling_climax(bar: dict) -> Optional[dict]:
    """
    Selling Climax: panic selling about to exhaust.
    Ultra-high volume + wide/ultra-wide down bar + close in middle or upper half.
    """
    if bar["vol_class"] != "ultra_high":
        return None
    if bar["spread_class"] not in ("wide", "ultra_wide"):
        return None
    if not bar["is_down"]:
        return None
    if bar["close_pos"] < 0.5:
        return None
    return {
        "pattern": "Selling Climax",
        "bias": "bullish",
        "strength": 2,
        "desc": "Ultra-high volume down bar closing strong — selling exhaustion",
    }


def _detect_no_demand(bar: dict) -> Optional[dict]:
    """
    No Demand: up bar on low volume with narrow spread.
    Means no buying interest — bearish.
    """
    if bar["vol_class"] != "low":
        return None
    if bar["spread_class"] not in ("narrow", "average"):
        return None
    if not bar["is_up"]:
        return None
    return {
        "pattern": "No Demand",
        "bias": "bearish",
        "strength": 1,
        "desc": "Up bar on low volume — no buying interest",
    }


def _detect_no_supply(bar: dict) -> Optional[dict]:
    """
    No Supply: down bar on low volume with narrow spread.
    Means sellers are exhausted — bullish.
    """
    if bar["vol_class"] != "low":
        return None
    if bar["spread_class"] not in ("narrow", "average"):
        return None
    if not bar["is_down"]:
        return None
    return {
        "pattern": "No Supply",
        "bias": "bullish",
        "strength": 1,
        "desc": "Down bar on low volume — sellers exhausted",
    }


def _detect_test(bars: List[dict]) -> Optional[dict]:
    """
    Test: price dips into previous support area on LOW volume, then recovers.
    Look at last 3 bars: current bar is up, previous dipped on low volume.
    """
    if len(bars) < 3:
        return None
    prev = bars[-2]
    curr = bars[-1]

    if prev["vol_class"] != "low":
        return None
    if not prev["is_down"]:
        return None
    if not curr["is_up"]:
        return None
    if curr["close_pos"] < 0.5:
        return None

    return {
        "pattern": "Test",
        "bias": "bullish",
        "strength": 2,
        "desc": "Low-volume dip followed by recovery — successful test of support",
    }


def _detect_upthrust(bars: List[dict]) -> Optional[dict]:
    """
    Upthrust: push above previous highs on volume that fails (closes weak).
    Current bar has high volume, pushed up but closed in lower half.
    """
    if len(bars) < 3:
        return None
    curr = bars[-1]
    prev_high = max(b["high"] for b in bars[-4:-1]) if len(bars) >= 4 else bars[-2]["high"]

    if curr["high"] <= prev_high:
        return None
    if curr["vol_class"] not in ("high", "ultra_high"):
        return None
    if curr["close_pos"] > 0.4:
        return None

    return {
        "pattern": "Upthrust",
        "bias": "bearish",
        "strength": 2,
        "desc": "Push above resistance closing weak on high volume — bull trap",
    }


def _detect_effort_no_result(bars: List[dict]) -> Optional[dict]:
    """
    Effort vs Result: high volume but narrow spread = effort without result.
    Bearish if up bar (buying absorbed), bullish if down bar (selling absorbed).
    """
    curr = bars[-1]
    if curr["vol_class"] not in ("high", "ultra_high"):
        return None
    if curr["spread_class"] != "narrow":
        return None

    if curr["is_up"]:
        return {
            "pattern": "Effort No Result ↑",
            "bias": "bearish",
            "strength": 1,
            "desc": "High volume up bar with narrow spread — buying absorbed by supply",
        }
    elif curr["is_down"]:
        return {
            "pattern": "Effort No Result ↓",
            "bias": "bullish",
            "strength": 1,
            "desc": "High volume down bar with narrow spread — selling absorbed by demand",
        }
    return None


# ── Main VPA Analysis ───────────────────────────────────────────────────

def analyze_vpa(df: pd.DataFrame, lookback: int = 5) -> dict:
    """
    Run Volume Price Analysis on the last N bars.

    Args:
        df: OHLCV DataFrame (must have Open, High, Low, Close, Volume columns)
        lookback: number of recent bars to analyze (default: 5)

    Returns:
        dict with:
            vpa_score: int — net VPA score (positive = bullish, negative = bearish)
            vpa_bias: str — "bullish", "bearish", or "neutral"
            patterns: list of detected pattern dicts
            latest_pattern: str — most significant pattern name or ""
    """
    if len(df) < 30:
        return {"vpa_score": 0, "vpa_bias": "neutral", "patterns": [], "latest_pattern": ""}

    # Compute average spread and volume over 20 bars (before the lookback window)
    recent = df.tail(lookback + 20)
    avg_window = recent.iloc[:-lookback] if len(recent) > lookback else recent.iloc[:20]
    avg_spread = (avg_window["High"] - avg_window["Low"]).mean()
    avg_volume = avg_window["Volume"].mean()

    # Build bar analysis for the lookback window
    analysis_bars = []
    target_bars = df.tail(lookback)
    for idx in range(len(target_bars)):
        row = target_bars.iloc[idx]
        o, h, l, c, v = row["Open"], row["High"], row["Low"], row["Close"], row["Volume"]
        spread = h - l
        bar = {
            "open": o, "high": h, "low": l, "close": c, "volume": v,
            "spread": spread,
            "close_pos": _close_position(o, h, l, c),
            "spread_class": _classify_spread(spread, avg_spread),
            "vol_class": _classify_volume(v, avg_volume),
            "is_up": _is_up_bar(o, c),
            "is_down": _is_down_bar(o, c),
        }
        analysis_bars.append(bar)

    # Detect patterns on each bar (prioritize latest)
    all_patterns = []
    detectors_single = [
        _detect_accumulation,
        _detect_distribution,
        _detect_buying_climax,
        _detect_selling_climax,
        _detect_no_demand,
        _detect_no_supply,
    ]

    for i, bar in enumerate(analysis_bars):
        for detector in detectors_single:
            result = detector(bar)
            if result:
                result["bar_index"] = i
                result["recency"] = i / max(len(analysis_bars) - 1, 1)  # 0=oldest, 1=newest
                all_patterns.append(result)

    # Multi-bar patterns (need context)
    if len(analysis_bars) >= 3:
        for detector in [_detect_test, _detect_upthrust, _detect_effort_no_result]:
            result = detector(analysis_bars)
            if result:
                result["bar_index"] = len(analysis_bars) - 1
                result["recency"] = 1.0
                all_patterns.append(result)

    # Compute VPA score: recent patterns weighted more heavily
    vpa_score = 0
    for p in all_patterns:
        weight = 0.5 + 0.5 * p["recency"]  # 0.5x for oldest, 1.0x for newest
        points = p["strength"] * 5  # strength 1 = ±5, strength 2 = ±10
        if p["bias"] == "bullish":
            vpa_score += int(points * weight)
        elif p["bias"] == "bearish":
            vpa_score -= int(points * weight)

    # Determine bias
    if vpa_score >= 5:
        vpa_bias = "bullish"
    elif vpa_score <= -5:
        vpa_bias = "bearish"
    else:
        vpa_bias = "neutral"

    # Latest significant pattern (most recent, highest strength)
    latest_pattern = ""
    if all_patterns:
        latest = sorted(all_patterns, key=lambda p: (p["recency"], p["strength"]), reverse=True)[0]
        latest_pattern = latest["pattern"]

    return {
        "vpa_score": vpa_score,
        "vpa_bias": vpa_bias,
        "patterns": all_patterns,
        "latest_pattern": latest_pattern,
    }


def analyze_vpa_at(df: pd.DataFrame, end_idx: int, lookback: int = 5) -> dict:
    """
    Point-in-time VPA analysis (for backtesting — no look-ahead bias).
    Analyzes bars ending at end_idx.
    """
    if end_idx < 30:
        return {"vpa_score": 0, "vpa_bias": "neutral", "patterns": [], "latest_pattern": ""}
    sliced = df.iloc[:end_idx + 1]
    return analyze_vpa(sliced, lookback=lookback)
