"""
Trade Summary Generator — Template-based natural language stock summaries.
No AI provider needed; uses indicator data to compose analyst-style text.
"""


def format_trade_summary(detail: dict) -> dict:
    """
    Generate a full trade summary and mini one-liner from stock detail data.

    Returns:
        {"full": str, "mini": str, "verdict": str, "color": str}
    """
    a = detail.get("analysis", {})
    ind = detail.get("indicators", {})
    risk = detail.get("risk", {})
    ep = detail.get("entry_plan")
    mtf = detail.get("mtf", {})
    vpa = detail.get("vpa", {})

    signal = a.get("signal", "HOLD")
    net_score = a.get("net_score", 0)
    grade = detail.get("grade", "C")
    grade_label = detail.get("grade_label", "")
    name = detail.get("name", detail.get("symbol", ""))
    symbol = detail.get("symbol", "")
    close = detail.get("close", 0)

    # --- Build sentences ---
    parts = []

    # 1. Opening verdict
    verdict, color = _verdict(signal, grade)
    parts.append(f"{name} ({symbol}) — {_grade_text(grade, grade_label)}, {signal} (Score: {net_score}).")

    # 2. Trend context (EMA positions)
    trend_line = _trend_sentence(ind, close)
    if trend_line:
        parts.append(trend_line)

    # 3. Momentum (RSI + ADX)
    momentum_line = _momentum_sentence(ind)
    if momentum_line:
        parts.append(momentum_line)

    # 4. VPA insight
    vpa_line = _vpa_sentence(vpa)
    if vpa_line:
        parts.append(vpa_line)

    # 5. Multi-timeframe
    mtf_line = _mtf_sentence(mtf)
    if mtf_line:
        parts.append(mtf_line)

    # 6. Action recommendation
    action_line = _action_sentence(signal, ep, risk)
    if action_line:
        parts.append(action_line)

    # 7. Risk closing
    risk_line = _risk_sentence(risk)
    if risk_line:
        parts.append(risk_line)

    full = " ".join(parts)

    # Mini one-liner for scanner tooltip
    mini = _build_mini(signal, grade, ind, vpa, risk)

    return {
        "full": full,
        "mini": mini,
        "verdict": verdict,
        "color": color,
    }


def _verdict(signal: str, grade: str) -> tuple:
    """Return (verdict_text, tailwind_color) based on signal + grade."""
    if signal == "STRONG BUY" and grade in ("A", "B"):
        return "Strong Opportunity", "green"
    if signal in ("STRONG BUY", "BUY") and grade in ("A", "B"):
        return "Good Setup", "green"
    if signal in ("STRONG BUY", "BUY") and grade == "C":
        return "Emerging Potential", "blue"
    if signal == "WATCH":
        return "Wait & Monitor", "yellow"
    if signal in ("SELL", "STRONG SELL"):
        return "Avoid / Exit", "red"
    return "Neutral", "gray"


def _grade_text(grade: str, label: str) -> str:
    if label:
        return f"Grade {grade} ({label})"
    return f"Grade {grade}"


def _trend_sentence(ind: dict, close: float) -> str:
    ema20 = ind.get("ema_20", 0)
    ema50 = ind.get("ema_50", 0)
    ema200 = ind.get("ema_200", 0)

    if not all([ema20, ema50, ema200, close]):
        return ""

    above_all = close > ema20 > ema50 > ema200
    below_all = close < ema20 < ema50 < ema200
    above_20_50 = close > ema20 and close > ema50

    if above_all:
        return "Price is above all major EMAs (20/50/200) — strong uptrend structure."
    elif below_all:
        return "Price is below all major EMAs — downtrend structure, caution advised."
    elif above_20_50:
        return "Price is above EMA 20 and 50, showing short-term bullish momentum."
    elif close > ema20:
        return "Price is above EMA 20 but below longer averages — mixed trend."
    elif close < ema20 and close < ema50:
        return "Price is below EMA 20 and 50 — short-term weakness."
    return ""


def _momentum_sentence(ind: dict) -> str:
    rsi = ind.get("rsi")
    adx = ind.get("adx")

    parts = []

    if rsi is not None:
        if rsi > 70:
            parts.append(f"RSI at {rsi:.0f} is overbought — pullback risk is high")
        elif rsi > 55:
            parts.append(f"RSI at {rsi:.0f} shows healthy bullish momentum with room to run")
        elif rsi > 45:
            parts.append(f"RSI at {rsi:.0f} is neutral — no strong momentum either way")
        elif rsi > 30:
            parts.append(f"RSI at {rsi:.0f} is on the weak side but not yet oversold")
        else:
            parts.append(f"RSI at {rsi:.0f} is oversold — potential bounce setup")

    if adx is not None:
        if adx > 30:
            parts.append(f"ADX at {adx:.0f} confirms a strong trend")
        elif adx > 20:
            parts.append(f"ADX at {adx:.0f} shows a developing trend")
        else:
            parts.append(f"ADX at {adx:.0f} indicates weak/no trend")

    if parts:
        return ". ".join(parts) + "."
    return ""


def _vpa_sentence(vpa: dict) -> str:
    if not vpa:
        return ""

    bias = vpa.get("vpa_bias", "neutral")
    pattern = vpa.get("latest_pattern", "")
    score = vpa.get("vpa_score", 0)

    if not pattern or pattern == "None":
        return ""

    if bias == "bullish" and score > 0:
        return f"VPA detects \"{pattern}\" — smart money appears to be buying (VPA score: +{score})."
    elif bias == "bearish" and score < 0:
        return f"VPA detects \"{pattern}\" — distribution activity detected (VPA score: {score})."
    elif pattern:
        return f"VPA shows \"{pattern}\" pattern (score: {score})."
    return ""


def _mtf_sentence(mtf: dict) -> str:
    score = mtf.get("score", 0)
    desc = mtf.get("desc", "")
    if not desc:
        return ""
    if score > 0:
        return f"Weekly timeframe confirms: {desc} (+{score} bonus)."
    elif score < 0:
        return f"Weekly timeframe warns: {desc} ({score} penalty)."
    return ""


def _action_sentence(signal: str, ep: dict, risk: dict) -> str:
    risk_level = risk.get("level", "Medium") if risk else "Medium"

    if signal in ("STRONG BUY", "BUY"):
        if ep:
            sl_pct = ep.get("stop_pct", 0)
            tp_pct = ep.get("target_pct", 0)
            rr = ep.get("rr_ratio", 0)
            line = f"Entry at RM {ep['entry']:.3f}, Stop-Loss RM {ep['stop_loss']:.3f} (-{sl_pct:.1f}%), Target RM {ep['take_profit']:.3f} (+{tp_pct:.1f}%), R:R 1:{rr:.1f}."
            if rr >= 1.5:
                line += " Favorable risk/reward."
            elif rr < 1:
                line += " ⚠️ Risk/reward below 1:1 — consider waiting for better entry."
            return line
        return "BUY signal active — check entry plan for position sizing."
    elif signal == "WATCH":
        return "Not actionable yet — monitor for signal improvement before entering."
    elif signal in ("SELL", "STRONG SELL"):
        return "Exit or avoid this stock. Bearish signals dominate."
    return ""


def _risk_sentence(risk: dict) -> str:
    if not risk:
        return ""

    level = risk.get("level", "Medium")
    warnings = risk.get("warnings", [])

    if level == "High" and warnings:
        top_warns = ", ".join(warnings[:2]).lower()
        return f"⚠️ High risk — {top_warns}."
    elif level == "Low":
        return "✅ Low risk profile — favorable conditions."
    elif level == "Medium":
        return "Risk level is moderate — standard position sizing recommended."
    return ""


def _build_mini(signal: str, grade: str, ind: dict, vpa: dict, risk: dict) -> str:
    """One-liner summary for scanner tooltip."""
    parts = [signal, f"Grade {grade}"]

    rsi = ind.get("rsi")
    if rsi is not None:
        parts.append(f"RSI {rsi:.0f}")

    adx = ind.get("adx")
    if adx is not None:
        parts.append(f"ADX {adx:.0f}")

    if vpa:
        pattern = vpa.get("latest_pattern", "")
        if pattern and pattern != "None":
            parts.append(f"VPA: {pattern}")

    if risk:
        parts.append(f"Risk: {risk.get('level', '?')}")

    return " | ".join(parts)
