"""
Buy/Sell signal scoring engine.
Each signal contributes a weighted score. Stocks are ranked by total score.
"""

import pandas as pd


# ═══════════════════════════════════════════════════════════════════
# Score weights (total possible BUY ~ +100, SELL ~ -100)
# ═══════════════════════════════════════════════════════════════════

def compute_buy_score(ind: dict) -> tuple[int, list[str]]:
    """
    Compute a BUY score from indicator values.
    Returns (score, list_of_reasons).
    """
    score = 0
    reasons = []

    close = ind.get("close")
    if close is None:
        return 0, []

    # ── Trend: Price above EMA 50 & 200 ──
    ema_50 = ind.get("ema_50")
    ema_200 = ind.get("ema_200")
    if ema_50 and ema_200:
        if close > ema_50 > ema_200:
            score += 20
            reasons.append("Strong uptrend (Price > EMA50 > EMA200)")
        elif close > ema_50:
            score += 10
            reasons.append("Above EMA50")
        elif close > ema_200:
            score += 5
            reasons.append("Above EMA200")

    # ── EMA 20 crossover (short-term momentum) ──
    ema_20 = ind.get("ema_20")
    if ema_20 and ema_50:
        if ema_20 > ema_50 and close > ema_20:
            score += 10
            reasons.append("EMA20 above EMA50 (momentum)")

    # ── MACD bullish crossover ──
    macd_hist = ind.get("macd_hist")
    macd_hist_prev = ind.get("macd_hist_prev")
    if macd_hist is not None and macd_hist_prev is not None:
        if macd_hist > 0 and macd_hist_prev <= 0:
            score += 15
            reasons.append("MACD bullish crossover ↑")
        elif macd_hist > 0:
            score += 5
            reasons.append("MACD positive")

    # ── RSI sweet spot (40-65 = momentum building, not overbought) ──
    rsi = ind.get("rsi")
    if rsi is not None:
        if 40 <= rsi <= 65:
            score += 15
            reasons.append(f"RSI {rsi:.0f} (momentum zone)")
        elif 30 <= rsi < 40:
            score += 10
            reasons.append(f"RSI {rsi:.0f} (oversold bounce)")
        elif rsi < 30:
            score += 5
            reasons.append(f"RSI {rsi:.0f} (deeply oversold)")

    # ── ADX trend strength ──
    adx = ind.get("adx")
    di_plus = ind.get("di_plus")
    di_minus = ind.get("di_minus")
    if adx is not None and di_plus is not None and di_minus is not None:
        if adx > 25 and di_plus > di_minus:
            score += 15
            reasons.append(f"Strong bullish trend (ADX {adx:.0f})")
        elif adx > 20 and di_plus > di_minus:
            score += 8
            reasons.append(f"Moderate trend (ADX {adx:.0f})")

    # ── Volume confirmation ──
    volume = ind.get("volume")
    vol_sma = ind.get("volume_sma_20")
    if volume and vol_sma and vol_sma > 0:
        vol_ratio = volume / vol_sma
        if vol_ratio > 1.5:
            score += 15
            reasons.append(f"High volume ({vol_ratio:.1f}x avg)")
        elif vol_ratio > 1.0:
            score += 5
            reasons.append(f"Above avg volume ({vol_ratio:.1f}x)")

    # ── OBV trending up ──
    obv = ind.get("obv")
    obv_sma = ind.get("obv_sma_20")
    if obv is not None and obv_sma is not None:
        if obv > obv_sma:
            score += 5
            reasons.append("OBV rising (accumulation)")

    # ── Price near 52-week low (value opportunity) ──
    low_52w = ind.get("low_52w")
    high_52w = ind.get("high_52w")
    if low_52w and high_52w and high_52w > low_52w:
        position = (close - low_52w) / (high_52w - low_52w)
        if position < 0.3:
            score += 5
            reasons.append("Near 52-week low (value zone)")

    # ── Bollinger Band bounce ──
    bb_lower = ind.get("bb_lower")
    bb_mid = ind.get("bb_mid")
    if bb_lower and bb_mid:
        if close <= bb_lower * 1.02:
            score += 5
            reasons.append("Near Bollinger lower band (bounce)")

    return score, reasons


def compute_sell_score(ind: dict) -> tuple[int, list[str]]:
    """
    Compute a SELL score (negative = stronger sell signal).
    Returns (score, list_of_reasons).
    """
    score = 0
    reasons = []

    close = ind.get("close")
    if close is None:
        return 0, []

    # ── Price below EMA 50 ──
    ema_50 = ind.get("ema_50")
    ema_200 = ind.get("ema_200")
    if ema_50 and ema_200:
        if close < ema_50 < ema_200:
            score -= 20
            reasons.append("Downtrend (Price < EMA50 < EMA200)")
        elif close < ema_50:
            score -= 10
            reasons.append("Below EMA50")

    # ── MACD bearish crossover ──
    macd_hist = ind.get("macd_hist")
    macd_hist_prev = ind.get("macd_hist_prev")
    if macd_hist is not None and macd_hist_prev is not None:
        if macd_hist < 0 and macd_hist_prev >= 0:
            score -= 15
            reasons.append("MACD bearish crossover ↓")
        elif macd_hist < 0:
            score -= 5
            reasons.append("MACD negative")

    # ── RSI overbought ──
    rsi = ind.get("rsi")
    if rsi is not None:
        if rsi > 75:
            score -= 15
            reasons.append(f"RSI {rsi:.0f} (overbought)")
        elif rsi > 70:
            score -= 8
            reasons.append(f"RSI {rsi:.0f} (getting overbought)")

    # ── ADX declining / bearish ──
    adx = ind.get("adx")
    di_plus = ind.get("di_plus")
    di_minus = ind.get("di_minus")
    if adx is not None and di_plus is not None and di_minus is not None:
        if di_minus > di_plus and adx > 25:
            score -= 15
            reasons.append(f"Strong bearish trend (ADX {adx:.0f})")
        elif adx < 20:
            score -= 5
            reasons.append(f"Weak/no trend (ADX {adx:.0f})")

    # ── Volume declining on price rise (distribution) ──
    volume = ind.get("volume")
    vol_sma = ind.get("volume_sma_20")
    obv = ind.get("obv")
    obv_sma = ind.get("obv_sma_20")
    if obv is not None and obv_sma is not None:
        if obv < obv_sma:
            score -= 5
            reasons.append("OBV falling (distribution)")

    # ── Near 52-week high (resistance) ──
    high_52w = ind.get("high_52w")
    low_52w = ind.get("low_52w")
    if high_52w and low_52w and high_52w > low_52w:
        position = (close - low_52w) / (high_52w - low_52w)
        if position > 0.95:
            score -= 10
            reasons.append("At 52-week high (resistance)")
        elif position > 0.85:
            score -= 5
            reasons.append("Near 52-week high")

    # ── Bollinger upper band ──
    bb_upper = ind.get("bb_upper")
    if bb_upper and close >= bb_upper * 0.98:
        score -= 5
        reasons.append("Near Bollinger upper band")

    return score, reasons


def classify_signal(buy_score: int, sell_score: int) -> str:
    """Classify overall signal as STRONG BUY / BUY / HOLD / SELL / STRONG SELL."""
    net = buy_score + sell_score  # sell_score is already negative
    return classify_net_score(net)


def classify_net_score(net: int) -> str:
    """Classify signal from a final adjusted net score."""
    if net >= 60:
        return "STRONG BUY"
    elif net >= 35:
        return "BUY"
    elif net >= 10:
        return "WATCH"
    elif net >= -20:
        return "HOLD"
    elif net >= -45:
        return "SELL"
    else:
        return "STRONG SELL"


def analyze_stock(ind: dict) -> dict:
    """Full analysis for a single stock. Returns signal data."""
    buy_score, buy_reasons = compute_buy_score(ind)
    sell_score, sell_reasons = compute_sell_score(ind)
    signal = classify_signal(buy_score, sell_score)

    return {
        "buy_score": buy_score,
        "sell_score": sell_score,
        "net_score": buy_score + sell_score,
        "signal": signal,
        "buy_reasons": buy_reasons,
        "sell_reasons": sell_reasons,
    }
