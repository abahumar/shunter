# Fundamental Analysis Integration Guide

## Quick Start: 3-Step Integration

### STEP 1: Enhance Data Fetching
**File:** `scanner/data_fetcher.py`

Replace `fetch_stock_info()` (lines 29-42):

```python
def fetch_stock_info(symbol: str) -> dict:
    """Fetch fundamental info including P/E, dividend, debt metrics."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "eps_growth": info.get("epsTrailingTwelveMonths"),
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector", "Unknown"),
            "name": info.get("shortName", symbol),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
        }
    except Exception:
        return {}
```

---

### STEP 2: Create Fundamental Scoring Module
**File:** `scanner/fundamentals.py` (NEW FILE)

```python
"""
Fundamental analysis scoring for Malaysian stocks.
Complements technical signals with value/quality metrics.
"""

def compute_fundamental_score(info: dict) -> tuple[int, list[str]]:
    """
    Score based on P/E, dividend, debt, ROE metrics.
    Returns (score, reasons).
    Max score: ~40 points.
    """
    score = 0
    reasons = []
    
    if not info:
        return 0, []
    
    # ── P/E Valuation ──
    pe = info.get("pe_ratio")
    if pe and pe > 0:
        if 8 <= pe <= 16:  # Reasonable for Malaysia
            score += 12
            reasons.append(f"Fair P/E {pe:.1f} (8-16 range)")
        elif 5 <= pe < 8:
            score += 8
            reasons.append(f"Low P/E {pe:.1f} (undervalued?)")
        elif pe > 25:
            score -= 5
            reasons.append(f"High P/E {pe:.1f} (expensive)")
    
    # ── Dividend Yield ──
    div_yield = info.get("dividend_yield")
    if div_yield and div_yield > 0:
        if div_yield >= 0.05:  # 5%+
            score += 10
            reasons.append(f"High dividend yield {div_yield*100:.2f}%")
        elif div_yield >= 0.03:  # 3-5%
            score += 5
            reasons.append(f"Good dividend yield {div_yield*100:.2f}%")
    
    # ── Return on Equity (ROE) ──
    roe = info.get("roe")
    if roe and roe > 0:
        if roe >= 0.15:  # 15%+
            score += 8
            reasons.append(f"Strong ROE {roe*100:.1f}%")
        elif roe >= 0.10:  # 10-15%
            score += 4
            reasons.append(f"Good ROE {roe*100:.1f}%")
    
    # ── Return on Assets (ROA) ──
    roa = info.get("roa")
    if roa and roa > 0:
        if roa >= 0.10:
            score += 4
            reasons.append(f"Strong ROA {roa*100:.1f}%")
    
    # ── Debt/Equity Ratio (lower is better) ──
    debt_to_equity = info.get("debt_to_equity")
    if debt_to_equity and debt_to_equity > 0:
        if debt_to_equity <= 0.5:  # Conservative
            score += 6
            reasons.append(f"Low leverage {debt_to_equity:.2f}x")
        elif debt_to_equity <= 1.0:
            score += 3
            reasons.append(f"Moderate leverage {debt_to_equity:.2f}x")
        elif debt_to_equity > 2.0:
            score -= 5
            reasons.append(f"High leverage {debt_to_equity:.2f}x")
    
    # ── Payout Ratio (sustainability) ──
    payout = info.get("payout_ratio")
    if payout and payout > 0:
        if payout <= 0.50:  # <50% sustainable
            score += 3
            reasons.append(f"Sustainable payout {payout*100:.0f}%")
        elif payout > 0.80:
            score -= 3
            reasons.append(f"High payout {payout*100:.0f}% (risky)")
    
    # ── Current/Quick Ratio (liquidity) ──
    current_ratio = info.get("current_ratio")
    if current_ratio and current_ratio >= 1.5:
        score += 3
        reasons.append(f"Good liquidity CR {current_ratio:.2f}x")
    
    return score, reasons
```

---

### STEP 3: Integrate into Main Scan
**File:** `scanner/signals.py`

Modify `analyze_stock()` function (lines 231-244):

```python
def analyze_stock(ind: dict, info: dict = None) -> dict:
    """Full analysis for a single stock. Returns signal data."""
    buy_score, buy_reasons = compute_buy_score(ind)
    sell_score, sell_reasons = compute_sell_score(ind)
    
    # NEW: Add fundamental scoring
    fundamental_score = 0
    fundamental_reasons = []
    if info:
        from scanner.fundamentals import compute_fundamental_score
        fundamental_score, fundamental_reasons = compute_fundamental_score(info)
    
    signal = classify_signal(buy_score, sell_score)
    
    return {
        "buy_score": buy_score,
        "sell_score": sell_score,
        "fundamental_score": fundamental_score,  # NEW
        "net_score": buy_score + sell_score + fundamental_score,  # UPDATED
        "signal": signal,
        "buy_reasons": buy_reasons,
        "sell_reasons": sell_reasons,
        "fundamental_reasons": fundamental_reasons,  # NEW
    }
```

---

## Where to Call the Enhanced Functions

### For WEB SCANS (app.py)
**Location:** `_run_scan()` function, line 243-294

```python
for symbol, df in stock_data.items():
    try:
        df = compute_indicators(df)
        stock_data[symbol] = df
        ind = get_latest_indicators(df)
        
        # NEW: Fetch fundamental data
        fund_info = fetch_stock_info(symbol)
        
        # MODIFIED: Pass info to analyze_stock
        analysis = analyze_stock(ind, fund_info)
        
        # Store fundamental data
        analysis["fundamental_info"] = fund_info
        
        # Continue with existing logic...
        mtf_bonus, mtf_desc = multi_timeframe_score(df)
        analysis["net_score"] += mtf_bonus
        # ... etc
```

### For CLI SCANS (stock_hunter.py)
**Location:** `cmd_scan()` function, line 83-110

```python
for symbol, df in data.items():
    try:
        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        
        # NEW: Fetch fundamentals
        fund_info = fetch_stock_info(symbol)
        
        # MODIFIED: Pass info
        analysis = analyze_stock(ind, fund_info)
        
        # Continue with existing...
```

### For CLI CHECK (stock_hunter.py)
**Location:** `cmd_check()` function, line 184-186

```python
df = compute_indicators(df)
ind = get_latest_indicators(df)

# NEW: Fetch fundamentals
fund_info = fetch_stock_info(symbol)

# MODIFIED: Pass info
analysis = analyze_stock(ind, fund_info)

# Display in console
if analysis.get("fundamental_reasons"):
    console.print("\n[bold blue]📊 Fundamentals[/bold blue]:")
    for r in analysis["fundamental_reasons"]:
        console.print(f"  [blue]•[/blue] {r}")
```

### For AUTO SCAN (auto_scan.py)
**Location:** `run_scan()` function, line 38-62

```python
results = []
for symbol, df in data.items():
    try:
        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        
        # NEW: Fetch fundamentals
        fund_info = fetch_stock_info(symbol)
        
        # MODIFIED: Pass info
        analysis = analyze_stock(ind, fund_info)
        
        # Continue with existing...
```

### For BOT SCAN (bot.py)
**Location:** `handle_scan()` function, line 98-118

```python
for symbol, df in data.items():
    try:
        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        
        # NEW: Fetch fundamentals
        fund_info = fetch_stock_info(symbol)
        
        # MODIFIED: Pass info
        analysis = analyze_stock(ind, fund_info)
        
        # Continue...
```

Also modify `handle_check()` (line 164-166):

```python
df = compute_indicators(df)
ind = get_latest_indicators(df)

# NEW
fund_info = fetch_stock_info(symbol)
analysis = analyze_stock(ind, fund_info)

# In the message (add after line 216):
if analysis.get("fundamental_reasons"):
    msg += "\n<b>📊 Fundamentals</b>\n"
    for r in analysis["fundamental_reasons"][:3]:
        msg += f"  • {r}\n"
```

---

## Display Recommendations

### Web Dashboard (app.py templates)
Add fundamental section to stock cards:
```html
{% if result.fundamental_reasons %}
<div class="fundamentals">
    <h4>📊 Fundamentals (+{{ result.fundamental_score }})</h4>
    <ul>
    {% for reason in result.fundamental_reasons[:3] %}
        <li>{{ reason }}</li>
    {% endfor %}
    </ul>
</div>
{% endif %}
```

### Telegram Bot Output
Already handled by modifying `handle_check()` above

### CLI Output (stock_hunter.py)
```python
# In cmd_scan() - add column:
table.add_column("Fund Score", justify="right", width=9)

# In loop:
table.add_row(
    # ... existing fields
    str(r.get("fundamental_score", 0)),
)

# In cmd_check():
if analysis.get("fundamental_reasons"):
    console.print("\n[bold blue]📊 Fundamentals[/bold blue]:")
    for r in analysis["fundamental_reasons"]:
        console.print(f"  [blue]•[/blue] {r}")
```

---

## Testing

### Unit Test for Fundamental Scoring
**File:** `tests/test_fundamentals.py` (NEW)

```python
import pytest
from scanner.fundamentals import compute_fundamental_score

def test_high_dividend():
    info = {"dividend_yield": 0.06}
    score, reasons = compute_fundamental_score(info)
    assert score >= 10
    assert any("dividend" in r.lower() for r in reasons)

def test_fair_pe():
    info = {"pe_ratio": 12.0}
    score, reasons = compute_fundamental_score(info)
    assert score >= 8
    assert any("p/e" in r.lower() for r in reasons)

def test_high_leverage():
    info = {"debt_to_equity": 2.5}
    score, reasons = compute_fundamental_score(info)
    assert any("leverage" in r.lower() for r in reasons)
```

---

## Caveats & Limitations

1. **Yahoo Finance Malaysia Data:**
   - Not all fields available for Malaysian stocks
   - Some tickers may have incomplete/delayed data
   - Fallback gracefully: `info.get("field")` returns `None`

2. **Score Weight:**
   - Fundamental score max ~40 points (vs technical 100+)
   - Technical signals still dominate (appropriate for short-term trading)
   - Adjust weights if you want more fundamental influence

3. **Data Freshness:**
   - Fundamental data may be quarterly/annual
   - Less timely than technical indicators
   - Use as confirming signal, not standalone

4. **Missing Data Handling:**
   - If field is None, score doesn't add/subtract
   - Empty dict from `fetch_stock_info()` = 0 score
   - Gracefully degrades if API fails

---

## Performance Impact

- **Additional API Call:** ~0.3s per symbol (same as data fetch)
- **Processing:** Negligible (<5ms per stock)
- **Total Overhead:** ~5-10% slower (acceptable for daily scans)
- **Caching:** Consider caching fund_info for 24h to reduce calls

---

## Next Steps

1. **Add to data_fetcher.py** → enhance `fetch_stock_info()`
2. **Create fundamentals.py** → add scoring function
3. **Modify signals.py** → update `analyze_stock()`
4. **Update all callers** → pass `fund_info` parameter
5. **Test & verify** → check a few stocks manually
6. **Display enhancements** → show fundamental reasons in UI
7. **Optional:** Cache fundamental data for 24h to reduce API load

