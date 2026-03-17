# Stock Hunter Architecture - Quick Reference Card

## Data Flow: From Fetch → Scoring → Display

```
fetch_bulk_data(symbols)
    ↓ Returns Dict[symbol, DataFrame(OHLCV)]
    ↓
compute_indicators(df) + get_latest_indicators(df)
    ↓ Returns Dict{close, EMA20/50/200, RSI, ADX, MACD, ATR, Volume, ...}
    ↓
[NEW] fetch_stock_info(symbol)
    ↓ Returns Dict{pe_ratio, dividend_yield, debt_to_equity, roe, ...}
    ↓
analyze_stock(ind, info)
    ├─ compute_buy_score(ind) → (buy_score: 0-100, reasons)
    ├─ compute_sell_score(ind) → (sell_score: 0 to -100, reasons)
    ├─ [NEW] compute_fundamental_score(info) → (fund_score: 0-40, reasons)
    └─ Returns {buy_score, sell_score, fundamental_score, net_score, signal, reasons}
    ↓
[Additional Enhancements in app.py/_run_scan]
├─ multi_timeframe_score(df) → bonus ±15 points
├─ detect_volume_spike(df) → spike info or None
├─ compute_risk_score(ind) → {level: Low/Med/High, warnings}
├─ compute_confidence_grade(net_score, vol_ratio, mtf, risk, confirmed) → {grade: A-F}
└─ detect_emerging_setup(df, ind, score, grade) → emerging opportunities
    ↓
Results sorted by net_score → displayed/cached/sent
```

---

## Key Files & Their Roles

| File | Purpose | Key Functions | Input | Output |
|------|---------|---|---|---|
| `scanner/data_fetcher.py` | Get price & fundamental data | `fetch_bulk_data`, `fetch_stock_info` | symbols, period | Dict[sym, DF], Dict{pe, div, roe, ...} |
| `scanner/indicators.py` | Calculate technical indicators | `compute_indicators`, `get_latest_indicators` | OHLCV DataFrame | Dict{ema, rsi, adx, atr, ...} |
| `scanner/signals.py` | **CORE SCORING** | `analyze_stock`, `compute_buy_score`, `compute_sell_score` | ind dict | {signal, score, reasons} |
| `scanner/advanced.py` | Enhanced scoring & analysis | `multi_timeframe_score`, `compute_risk_score`, `compute_confidence_grade`, `detect_emerging_setup` | df, ind | (bonus, {grade}, {emerging}, {risk}) |
| `scanner/fundamentals.py` | **[NEW]** Fundamental scoring | `compute_fundamental_score` | info dict | (score, reasons) |
| `auto_scan.py` | Scheduled daily scan → Telegram | `run_scan`, `check_portfolio_alerts` | args | Telegram message |
| `bot.py` | Telegram bot commands | `handle_scan`, `handle_check`, `handle_sector` | chat_id, args | Telegram replies |
| `app.py` | Web dashboard & API | `_run_scan`, routes | request params | HTML/JSON responses |
| `stock_hunter.py` | CLI interface | `cmd_scan`, `cmd_check`, `cmd_portfolio` | CLI args | Rich console tables |

---

## Exact Function Signatures

### analyze_stock() - THE CORE
```python
# BEFORE
def analyze_stock(ind: dict) -> dict:
    # Returns: {buy_score, sell_score, net_score, signal, buy_reasons, sell_reasons}

# AFTER (with fundamentals)
def analyze_stock(ind: dict, info: dict = None) -> dict:
    # Returns: {buy_score, sell_score, fundamental_score, net_score, signal, 
    #           buy_reasons, sell_reasons, fundamental_reasons}
```

### compute_fundamental_score() - NEW
```python
def compute_fundamental_score(info: dict) -> tuple[int, list[str]]:
    """
    Scores P/E, dividend yield, ROE, debt ratios.
    Returns (score: 0-40, reasons: ["Fair P/E 12", "High dividend 5%", ...])
    """
```

### fetch_stock_info() - ENHANCED
```python
# BEFORE
def fetch_stock_info(symbol: str) -> dict:
    # Returns: {pe_ratio, market_cap, sector, name, current_price}

# AFTER (add fundamentals)
def fetch_stock_info(symbol: str) -> dict:
    # Returns: {...above plus...}
    #          {pe_ratio, eps, dividend_yield, payout_ratio, roe, roa, 
    #           debt_to_equity, current_ratio, revenue_growth, ...}
```

---

## Where Results Flow

### WEB (app.py)
```
_run_scan() → 
  for each stock:
    fetch_stock_info() → analyze_stock(ind, info) → 
      [MTF, risk, grade, emerging, VPA] → 
    results[] → 
  sort by net_score → 
  _cache_set() + _save_to_disk() →
  
Dashboard: displays top signals + grade A/B
Scanner: full results with all scores
Stock detail: all indicators + fundamental info
```

### TELEGRAM BOT (bot.py)
```
/scan command →
  for each stock:
    fetch_stock_info() → analyze_stock(ind, info) →
    format as HTML →
  reply with top 15 signals
  
/check command →
  fetch_stock_info() → analyze_stock(ind, info) →
  format detailed message with:
    - Indicators (RSI, ADX, EMA, etc)
    - Buy/sell reasons (technical + fundamental)
    - Support/Resistance
    - Volume spike
    - Position sizing
    - Confidence grade
```

### CLI (stock_hunter.py)
```
scan command →
  for each stock:
    fetch_stock_info() → analyze_stock(ind, info) →
    display as Rich table with columns:
      Symbol | Price | Signal | Score | RSI | ADX | Vol | Reasons
      (can add fundamental_score column)
      
check command →
  fetch_stock_info() → analyze_stock(ind, info) →
  display in Rich panels:
    - Stock header
    - Indicators table
    - ✓ Buy reasons (technical + fundamental)
    - ✗ Sell reasons
    - MTF analysis
    - Support/Resistance
    - Position sizing
```

### TELEGRAM AUTO (auto_scan.py)
```
run_scan() →
  for each stock:
    fetch_stock_info() → analyze_stock(ind, info) →
  filter STRONG BUY / BUY →
  add MTF bonus + spike detection →
  format_scan_results() →
  send via Telegram
```

---

## Score Breakdown Example

### Stock: 5225.KL (MAYBANK)
```
Technical Scoring:
  ├─ EMA Trend:        +20 (Price > EMA50 > EMA200)
  ├─ MACD:             +5  (positive histogram)
  ├─ RSI:              +15 (45 zone = momentum building)
  ├─ ADX:              +10 (strong bullish trend)
  ├─ Volume:          +10  (1.3x average)
  └─ Technical Total: +60

Fundamental Scoring:
  ├─ P/E:             +8  (Fair at 12x)
  ├─ Dividend:       +10  (5.2% yield)
  ├─ ROE:            +6   (18% strong)
  ├─ Leverage:       +3   (0.4x D/E)
  └─ Fundamental:    +27

Advanced Scoring:
  ├─ Multi-TF:       +15 (both weekly & daily bullish)
  ├─ Confirmation:   +10 (was BUY last scan too)
  ├─ VPA:            +5  (volume price action positive)
  ├─ Emerging:       0   (already grade A)
  └─ Advanced:       +30

TOTAL NET SCORE: 60 + 27 + 30 = 117 → STRONG BUY
Confidence Grade: A (95 points)
Risk Level: Low (2 points)
```

---

## The 3 Scoring Layers

### Layer 1: Technical Scoring (signals.py)
- **compute_buy_score()** → 0-100 points
- **compute_sell_score()** → 0 to -100 points
- **Net score** = buy_score + sell_score

### Layer 2: Fundamental Scoring (fundamentals.py) **[NEW]**
- **compute_fundamental_score()** → 0-40 points
- Only positive fundamentals boost score
- Complements (doesn't override) technical signals

### Layer 3: Advanced Scoring (advanced.py)
- **multi_timeframe_score()** → ±15 points (confirmation)
- **Risk score** → {Low/Medium/High} classification
- **Confidence grade** → A-F quality rating
- **Emerging setup** → early opportunities
- Market sentiment adjustment (in app.py)
- VPA score adjustment (in app.py)

---

## Signal Classification

```
net_score >= 60      → STRONG BUY    (Grade: A+)
net_score >= 35      → BUY           (Grade: A, B)
net_score >= 10      → WATCH         (Grade: C)
net_score >= -20     → HOLD          (Grade: C-, D)
net_score >= -45     → SELL          (Grade: D, E)
net_score < -45      → STRONG SELL   (Grade: F)
```

---

## Where to Inject Fundamental Analysis

### ✅ EASIEST: Modify existing functions

1. **data_fetcher.py** lines 29-42
   - Extend `fetch_stock_info()` to return P/E, dividend, debt ratios, etc.

2. **Create scanner/fundamentals.py**
   - New `compute_fundamental_score(info) → (score, reasons)`

3. **signals.py** lines 231-244
   - Modify `analyze_stock(ind, info=None)`
   - Add fundamental_score to net_score calculation

4. **Call sites** (app.py, bot.py, stock_hunter.py, auto_scan.py)
   - Fetch `fund_info = fetch_stock_info(symbol)` 
   - Pass to `analyze_stock(ind, fund_info)`

### ⏱ Implementation Time
- Step 1 (enhance fetch): 10 min
- Step 2 (create fundamentals.py): 20 min
- Step 3 (modify analyze_stock): 5 min
- Step 4 (update callers): 15 min
- Step 5 (test): 15 min
- **Total: ~1 hour**

---

## Common Pitfalls

1. **❌ Forgetting to pass `info` parameter**
   ```python
   # WRONG
   analysis = analyze_stock(ind)  # no fundamentals!
   
   # RIGHT
   fund_info = fetch_stock_info(symbol)
   analysis = analyze_stock(ind, fund_info)
   ```

2. **❌ Making fundamental score too large**
   ```python
   # WRONG: 100 points for dividend
   if div > 0.05:
       score += 100
   
   # RIGHT: ~10 points max
   if div > 0.05:
       score += 10
   ```

3. **❌ Not handling missing data**
   ```python
   # WRONG: crashes if pe_ratio is None
   if info.get("pe_ratio") > 20:
       ...
   
   # RIGHT: gracefully skip
   pe = info.get("pe_ratio")
   if pe and pe > 20:
       ...
   ```

4. **❌ Ignoring API rate limits**
   ```python
   # WRONG: 100+ simultaneous requests
   # WOULD crash Yahoo Finance API
   
   # RIGHT: Already handled by fetch_bulk_data()
   # with 0.3s delay per stock
   ```

---

## Testing a Single Stock

```python
# Interactive test
from scanner.data_fetcher import fetch_stock_data, fetch_stock_info
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock
from scanner.fundamentals import compute_fundamental_score

symbol = "5225.KL"  # MAYBANK

# Fetch data
df = fetch_stock_data(symbol, "1y")
df = compute_indicators(df)
ind = get_latest_indicators(df)

# Fetch fundamentals
info = fetch_stock_info(symbol)

# Analyze
analysis = analyze_stock(ind, info)

# Print results
print(f"Symbol: {symbol}")
print(f"Price: {ind['close']:.2f}")
print(f"Signal: {analysis['signal']}")
print(f"Buy Score: {analysis['buy_score']}")
print(f"Sell Score: {analysis['sell_score']}")
print(f"Fundamental Score: {analysis.get('fundamental_score', 0)}")
print(f"Net Score: {analysis['net_score']}")
print("\nBuy Reasons:")
for r in analysis['buy_reasons']:
    print(f"  • {r}")
print("\nFundamental Reasons:")
for r in analysis.get('fundamental_reasons', []):
    print(f"  • {r}")
```

---

## Files to Check

- **Architecture:** `/Users/zamri/Downloads/Personal Project 2026/Stock-hunter/ARCHITECTURE.md`
- **Injection Guide:** `/Users/zamri/Downloads/Personal Project 2026/Stock-hunter/FUNDAMENTAL_INJECTION_GUIDE.md`
- **This Guide:** `/Users/zamri/Downloads/Personal Project 2026/Stock-hunter/QUICK_REFERENCE.md`

