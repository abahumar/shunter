"""
Fundamental analysis module for Stock Hunter.
Fetches and scores fundamental data (PE, PB, Dividend Yield, ROE, etc.)
to complement the technical scoring engine.

Inspired by stocks like TH Plantations (5112.KL):
- Low P/E (undervalued earnings)
- P/B < 1.0 (trading below book value)
- High dividend yield (income)
- Healthy balance sheet (low debt, good liquidity)
"""

import yfinance as yf
from typing import Dict, List, Optional, Tuple


def fetch_fundamentals(symbol: str) -> dict:
    """
    Fetch fundamental data for a single stock from Yahoo Finance.
    Returns dict with PE, PB, dividend yield, ROE, debt/equity, etc.
    Returns empty dict on failure.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info:
            return {}

        return {
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield") or info.get("trailingAnnualDividendYield"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "market_cap": info.get("marketCap"),
            "book_value": info.get("bookValue"),
            "eps": info.get("trailingEps"),
            "sector": info.get("sector", "Unknown"),
            "name": info.get("shortName", symbol),
        }
    except Exception:
        return {}


def fetch_bulk_fundamentals(
    symbols: List[str],
    on_progress=None,
) -> Dict[str, dict]:
    """
    Fetch fundamentals for multiple stocks.
    Returns dict mapping symbol -> fundamentals dict.
    """
    results = {}
    total = len(symbols)

    for i, symbol in enumerate(symbols):
        if on_progress and i % 20 == 0:
            on_progress(i, total, f"Fetching fundamentals {i}/{total}...")

        data = fetch_fundamentals(symbol)
        if data:
            results[symbol] = data

    if on_progress:
        on_progress(total, total, f"Fundamentals fetched for {len(results)} stocks")

    return results


def compute_fundamental_score(fund: dict) -> Tuple[int, List[str]]:
    """
    Compute a fundamental score based on value/income metrics.
    Max score: +30 points. Returns (score, reasons).

    Scoring logic (inspired by TH Plantations profile):
    - Low PE: undervalued earnings
    - Low PB: trading below book value (margin of safety)
    - High dividend: income + price floor support
    - Good ROE: efficient use of equity
    - Low debt: financial safety
    - Good liquidity: can meet obligations
    """
    score = 0
    reasons = []

    # ── P/E Ratio (lower = cheaper) ──
    pe = fund.get("pe_ratio")
    if pe is not None and pe > 0:
        if pe < 8:
            score += 8
            reasons.append(f"Very low PE {pe:.1f} (deep value)")
        elif pe < 12:
            score += 5
            reasons.append(f"Low PE {pe:.1f} (undervalued)")
        elif pe < 15:
            score += 2
            reasons.append(f"Fair PE {pe:.1f}")
        elif pe > 30:
            score -= 3
            reasons.append(f"High PE {pe:.1f} (expensive)")

    # ── P/B Ratio (below 1.0 = below book value) ──
    pb = fund.get("pb_ratio")
    if pb is not None and pb > 0:
        if pb < 0.7:
            score += 8
            reasons.append(f"PB {pb:.2f} (deep discount to NTA)")
        elif pb < 1.0:
            score += 5
            reasons.append(f"PB {pb:.2f} (below book value)")
        elif pb < 1.5:
            score += 2
            reasons.append(f"PB {pb:.2f} (near book value)")
        elif pb > 5.0:
            score -= 2
            reasons.append(f"PB {pb:.2f} (premium valuation)")

    # ── Dividend Yield (higher = better income) ──
    div_yield = fund.get("dividend_yield")
    if div_yield is not None and div_yield > 0:
        dy_pct = div_yield * 100
        if dy_pct >= 5.0:
            score += 6
            reasons.append(f"High dividend {dy_pct:.1f}% 💰")
        elif dy_pct >= 3.0:
            score += 3
            reasons.append(f"Good dividend {dy_pct:.1f}%")
        elif dy_pct >= 1.5:
            score += 1
            reasons.append(f"Dividend {dy_pct:.1f}%")

    # ── ROE (Return on Equity — profitability) ──
    roe = fund.get("roe")
    if roe is not None:
        roe_pct = roe * 100
        if roe_pct >= 15:
            score += 4
            reasons.append(f"Strong ROE {roe_pct:.1f}%")
        elif roe_pct >= 10:
            score += 3
            reasons.append(f"Good ROE {roe_pct:.1f}%")
        elif roe_pct >= 5:
            score += 1
            reasons.append(f"ROE {roe_pct:.1f}%")
        elif roe_pct < 0:
            score -= 3
            reasons.append(f"Negative ROE {roe_pct:.1f}%")

    # ── Debt/Equity (lower = safer) ──
    de = fund.get("debt_to_equity")
    if de is not None:
        de_ratio = de / 100 if de > 10 else de  # Yahoo sometimes returns as %
        if de_ratio < 0.3:
            score += 4
            reasons.append(f"Low debt D/E {de_ratio:.2f}")
        elif de_ratio < 0.7:
            score += 2
            reasons.append(f"Moderate debt D/E {de_ratio:.2f}")
        elif de_ratio > 1.5:
            score -= 2
            reasons.append(f"High debt D/E {de_ratio:.2f}")

    # ── Current Ratio (liquidity) ──
    cr = fund.get("current_ratio")
    if cr is not None:
        if cr >= 2.0:
            score += 2
            reasons.append(f"Strong liquidity CR {cr:.1f}")
        elif cr >= 1.5:
            score += 1
            reasons.append(f"Good liquidity CR {cr:.1f}")
        elif cr < 1.0:
            score -= 2
            reasons.append(f"Weak liquidity CR {cr:.1f}")

    # ── Earnings Growth bonus ──
    eg = fund.get("earnings_growth")
    if eg is not None:
        eg_pct = eg * 100
        if eg_pct > 20:
            score += 2
            reasons.append(f"Earnings growth {eg_pct:.0f}% ↑")
        elif eg_pct < -20:
            score -= 2
            reasons.append(f"Earnings decline {eg_pct:.0f}% ↓")

    return score, reasons


def classify_fundamental(score: int) -> str:
    """Classify fundamental quality from score."""
    if score >= 20:
        return "STRONG VALUE"
    elif score >= 12:
        return "VALUE"
    elif score >= 5:
        return "FAIR"
    elif score >= 0:
        return "NEUTRAL"
    else:
        return "WEAK"


def format_fundamentals_brief(fund: dict) -> str:
    """Format key fundamental metrics as a brief string for tables."""
    parts = []

    pe = fund.get("pe_ratio")
    if pe is not None and pe > 0:
        parts.append(f"PE:{pe:.1f}")

    pb = fund.get("pb_ratio")
    if pb is not None and pb > 0:
        parts.append(f"PB:{pb:.2f}")

    dy = fund.get("dividend_yield")
    if dy is not None and dy > 0:
        parts.append(f"DY:{dy*100:.1f}%")

    roe = fund.get("roe")
    if roe is not None:
        parts.append(f"ROE:{roe*100:.1f}%")

    return " | ".join(parts) if parts else "-"


def format_fundamentals_detail(fund: dict, fund_score: int, fund_reasons: list) -> str:
    """Format fundamentals for detailed stock view (CLI check command)."""
    lines = []

    pe = fund.get("pe_ratio")
    pb = fund.get("pb_ratio")
    dy = fund.get("dividend_yield")
    roe = fund.get("roe")
    de = fund.get("debt_to_equity")
    cr = fund.get("current_ratio")
    eg = fund.get("earnings_growth")
    pm = fund.get("profit_margin")

    if pe is not None and pe > 0:
        lines.append(f"P/E Ratio: {pe:.2f}")
    if pb is not None and pb > 0:
        lines.append(f"P/B Ratio: {pb:.2f}")
    if dy is not None and dy > 0:
        lines.append(f"Dividend Yield: {dy*100:.2f}%")
    if roe is not None:
        lines.append(f"ROE: {roe*100:.2f}%")
    if de is not None:
        de_val = de / 100 if de > 10 else de
        lines.append(f"Debt/Equity: {de_val:.2f}")
    if cr is not None:
        lines.append(f"Current Ratio: {cr:.2f}")
    if eg is not None:
        lines.append(f"Earnings Growth: {eg*100:.1f}%")
    if pm is not None:
        lines.append(f"Profit Margin: {pm*100:.1f}%")

    quality = classify_fundamental(fund_score)
    lines.append(f"Fundamental Score: {fund_score:+d} ({quality})")

    return lines


def format_fundamentals_telegram(fund: dict, fund_score: int, fund_reasons: list) -> str:
    """Format fundamentals for Telegram message."""
    msg = "<b>📊 Fundamentals</b>\n"

    pe = fund.get("pe_ratio")
    pb = fund.get("pb_ratio")
    dy = fund.get("dividend_yield")
    roe = fund.get("roe")
    de = fund.get("debt_to_equity")
    cr = fund.get("current_ratio")

    metrics = []
    if pe is not None and pe > 0:
        metrics.append(f"PE: {pe:.1f}")
    if pb is not None and pb > 0:
        metrics.append(f"PB: {pb:.2f}")
    if dy is not None and dy > 0:
        metrics.append(f"DY: {dy*100:.1f}%")
    if roe is not None:
        metrics.append(f"ROE: {roe*100:.1f}%")
    if de is not None:
        de_val = de / 100 if de > 10 else de
        metrics.append(f"D/E: {de_val:.2f}")
    if cr is not None:
        metrics.append(f"CR: {cr:.1f}")

    if metrics:
        msg += "  " + " | ".join(metrics) + "\n"

    quality = classify_fundamental(fund_score)
    msg += f"  Score: {fund_score:+d} ({quality})\n"

    if fund_reasons:
        for r in fund_reasons[:3]:
            msg += f"  • <i>{r}</i>\n"

    return msg
