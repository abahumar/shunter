# Stock Hunter Architecture - Deep Dive

## 1. SCANNER/DATA_FETCHER.PY - Data Fetching Layer

### Function Signatures & Returns

#### `fetch_stock_data(symbol: str, period: str = "1y") -> Optional[pd.DataFrame]`
- **Lines 13-26**
- **Fetches:** OHLCV data from Yahoo Finance
- **Returns:** DataFrame with columns `Open, High, Low, Close, Volume` or `None`
- **Validation:** Requires at least 50 bars of data
- **Error Handling:** Silent fail returns `None` on exception

#### `fetch_stock_info(symbol: str) -> dict`
- **Lines 29-42**
- **Fetches from Yahoo Finance .info:**
  - `pe_ratio` → `trailingPE`
  - `market_cap` → `marketCap`
  - `sector` → `sector` (defaults to "Unknown")
  - `name` → `shortName`
  - `current_price` → `currentPrice` or `regularMarketPrice`
- **Returns:** Dict with above fields, empty dict `{}` on error
- **Currently Used:** **NOT actively used in scoring** (present but unused)

#### `fetch_batch_download(symbols: List[str], period: str = "1y", chunk_size: int = 50, on_progress: Optional[Callable] = None) -> Dict[str, pd.DataFrame]`
- **Lines 45-95**
- **Signature Returns:** `Dict[str, pd.DataFrame]` mapping symbol → OHLCV DataFrame
- **Processing:**
  - Downloads in chunks of 50 (configurable) to avoid timeouts
  - Requires 50+ bars per stock
  - Progress callback fires for each chunk
  - Silently skips failed/delisted stocks
- **Used In:** `app.py` for web scan (line 234), `bot.py` for telegram
- **Return Structure:**
  ```python
  {
    "5225.KL": DataFrame,  # OHLCV with DatetimeIndex
    "1155.KL": DataFrame,
    ...
  }
  ```

#### `fetch_bulk_data(symbols: List[str], period: str = "1y", delay: float = 0.3) -> Dict[str, pd.DataFrame]`
- **Lines 98-132**
- **Signature Returns:** `Dict[str, pd.DataFrame]` (same structure as batch_download)
- **Processing:**
  - Single-symbol downloads with rate limiting (0.3s delay default)
  - Shows Progress bar with spinner
  - Reports skipped stocks at end
- **Used In:** `stock_hunter.py` CLI (line 77), `auto_scan.py` (line 35)

### Key Fields Already Fetched
From Yahoo Finance:
- `Open, High, Low, Close, Volume` (OHLCV)
- `Dividends` column (if present in yfinance data) - **used in app.py line 267-268**

---

## 2. SCANNER/SIGNALS.PY - Base Signal Scoring

### Function Signatures & Mechanics

#### `compute_buy_score(ind: dict) -> tuple[int, list[str]]`
- **Lines 13-119**
- **Returns:** `(score: int, reasons: List[str])`
- **Max BUY score:** ~100 points
- **Scoring Components:**
  1. **EMA Trend (20-30 points):**
     - Close > EMA50 > EMA200: +20
     - Close > EMA50: +10
     - Close > EMA200: +5
     - EMA20 > EMA50 + close > EMA20: +10
  
  2. **MACD Bullish (15-20 points):**
     - Bullish crossover (hist > 0 & prev ≤ 0): +15
     - Positive histogram: +5
  
  3. **RSI Momentum (5-15 points):**
     - 40-65 zone: +15
     - 30-40 zone: +10
     - <30: +5
  
  4. **ADX Trend Strength (8-15 points):**
     - ADX > 25 & DI+ > DI-: +15
     - ADX > 20 & DI+ > DI-: +8
  
  5. **Volume Confirmation (5-15 points):**
     - Volume > 1.5x SMA20: +15
     - Volume > 1.0x SMA20: +5
  
  6. **Other Signals (5 points each):**
     - OBV above SMA20
     - Price near 52-week low (<30%)
     - Price near Bollinger lower band

#### `compute_sell_score(ind: dict) -> tuple[int, list[str]]`
- **Lines 122-206**
- **Returns:** `(score: int, reasons: List[str])`
- **Max SELL score:** -100 points (negative)
- **Scoring Components:** Mirror of buy signals
  1. Downtrend signals (-20 to -10)
  2. MACD bearish (-15 to -5)
  3. RSI overbought (-15 to -8)
  4. ADX bearish (-15 to -5)
  5. Volume distribution (-5)
  6. 52-week high resistance (-10 to -5)
  7. Bollinger upper band (-5)

#### `analyze_stock(ind: dict) -> dict`
- **Lines 231-244**
- **Key Function:** Main entry point for signal analysis
- **Signature Returns:**
  ```python
  {
    "buy_score": int,
    "sell_score": int,
    "net_score": int,  # buy_score + sell_score
    "signal": str,     # from classify_signal()
    "buy_reasons": List[str],
    "sell_reasons": List[str],
  }
  ```
- **Calculation:** `net_score = buy_score + sell_score` (sell_score is already negative)

#### `classify_signal(buy_score: int, sell_score: int) -> str`
- **Lines 209-212**
- **Classification Logic:**
  ```
  net = buy_score + sell_score
  STRONG BUY: net >= 60
  BUY:        net >= 35
  WATCH:      net >= 10
  HOLD:       net >= -20
  SELL:       net >= -45
  STRONG SELL: net < -45
  ```

### What's Missing / Not Used Currently
- `fetch_stock_info()` data (P/E, market cap, sector) **NOT integrated into scoring**
- Dividend yield **only in app.py line 267-268**, not in signal scoring
- No fundamental analysis (P/E, EPS growth, debt, etc.)

---

## 3. SCANNER/ADVANCED.PY - Advanced Scoring Functions

### `multi_timeframe_score(df_daily: pd.DataFrame) -> Tuple[int, str]`
- **Lines 18-74**
- **Returns:** `(bonus_score: int, description: str)`
- **Resamples daily to weekly**, computes indicators on both
- **Scoring:**
  - Both bullish: +15
  - Both bearish: -15
  - Weekly bullish, daily pullback: +5
  - Weekly bearish, daily bounce: -5
  - Mixed: 0
- **Used In:** Every scan (app.py line 250, bot.py line 106, stock_hunter.py line 90)

### `find_support_resistance(df: pd.DataFrame, levels: int = 3) -> Dict[str, list]`
- **Lines 77-124**
- **Returns:**
  ```python
  {
    "support": [price1, price2, price3],      # sorted descending
    "resistance": [price1, price2, price3]    # sorted ascending
  }
  ```
- **Algorithm:** Local pivot points clustered within 2% threshold
- **Used In:** Stock detail pages (bot.py line 173, stock_hunter.py line 246, app.py line 511)

### `detect_volume_spike(df: pd.DataFrame, threshold: float = 2.5) -> Optional[dict]`
- **Lines 127-153**
- **Returns:**
  ```python
  {
    "volume_ratio": float,      # current_vol / avg_vol_20
    "avg_volume": float,
    "current_volume": float,
    "price_change": float,      # % change from prev day
    "type": str,                # "Bullish spike 🟢" or "Bearish spike 🔴"
  }
  # OR None if no spike detected
  ```
- **Threshold:** Default 2.5x (configurable)

### `get_dividend_yield(info: dict) -> Optional[float]`
- **Lines 156-158**
- **Returns:** Dividend yield percentage or None
- **Sources:** `dividendYield` or `trailingAnnualDividendYield`
- **Status:** **DEFINED but NEVER CALLED** in any of the main scanning code
- **⚠️ Injection Point:** Can integrate fundamental data here!

### `compute_risk_score(indicators: dict) -> dict`
- **Lines 213-283**
- **Returns:**
  ```python
  {
    "level": str,            # "Low" | "Medium" | "High"
    "points": int,           # risk score (0-10+)
    "warnings": List[str],   # ["High volatility (ATR >5%)", ...]
  }
  ```
- **Risk Factors:**
  1. **Volatility (ATR):** >5% = +3 points
  2. **RSI extremes:** >75 = +3, <25 = +2
  3. **Weak trend (ADX <15):** +2
  4. **Low volume (<0.5x avg):** +2
  5. **52-week high (>95%):** +3
- **Classification:**
  - High: >= 5 points
  - Medium: >= 2 points
  - Low: < 2 points
- **Used In:** app.py line 280, stock detail page

### `compute_confidence_grade(net_score: int, volume_ratio: float, mtf_desc: str, risk_level: str, confirmed: bool) -> dict`
- **Lines 286-376**
- **Returns:**
  ```python
  {
    "grade": str,          # "A" to "F"
    "label": str,          # "High Confidence" to "Avoid"
    "points": int,         # 0-100 scale
    "factors": List[str],  # ["Very strong score", "Strong volume", ...]
  }
  ```
- **Scoring (100-point scale):**
  - Score strength: 0-40 points
  - Volume: 0-20 points
  - Multi-timeframe: 0-20 points
  - Risk level: 0-10 points
  - Confirmation: 0-10 points (consecutive signals)
- **Grades:**
  - A: >= 75 points (High Confidence)
  - B: >= 55 points (Good)
  - C: >= 35 points (Moderate)
  - D: >= 20 points (Weak)
  - F: < 20 points (Avoid)
- **Used In:** app.py line 314-324, stock detail page

### `detect_emerging_setup(df: pd.DataFrame, indicators: dict, net_score: int, grade: str) -> Optional[dict]`
- **Lines 379-483**
- **Returns:**
  ```python
  {
    "is_emerging": True,
    "points": int,         # 0-13 max
    "reasons": List[str],  # ["MACD improving", "RSI in early momentum", ...]
  }
  # OR None if not emerging
  ```
- **Detects:** Grade C/D stocks trending toward B/A before crowd enters
- **Signals Checked:**
  1. MACD improving/bullish crossover: +2-3
  2. RSI in 40-55 zone (early momentum): +2
  3. Volume building 1.0-1.8x avg: +2
  4. Short-term trend turning: +2
  5. ADX 15-25 with DI+ leading: +2
  6. Price near Bollinger midline: +1
  7. Score 20-45 ("almost there"): +1
- **Threshold:** >= 5 points = emerging
- **Used In:** app.py line 335, for emerging opportunities

### `calculate_position_size(capital: float, price: float, stop_loss_pct: float = -10.0, max_risk_pct: float = 2.0, max_allocation_pct: float = 15.0) -> dict`
- **Lines 161-210**
- **Returns:**
  ```python
  {
    "lots": int,                # Bursa Malaysia lots (100 shares)
    "shares": int,              # Total shares
    "amount": float,            # RM to invest
    "risk_amount": float,       # RM at risk if SL hits
    "pct_of_capital": float,    # % allocation
    "price": float,             # Entry price
  }
  ```
- **Uses:** Min of risk-based OR allocation-based position sizing
- **Constraints:**
  - Max 2% capital risk per trade
  - Max 15% allocation per stock
  - Rounds down to Bursa Malaysia lots (100 shares)

### `calculate_entry_plan(close: float, atr: float, atr_multiplier: float = 2.0) -> Optional[dict]`
- **Lines 486-510**
- **Returns:**
  ```python
  {
    "entry": float,
    "stop_loss": float,         # close - (2 * atr)
    "take_profit": float,       # close + (3 * atr)
    "risk_per_share": float,
    "reward_per_share": float,
    "rr_ratio": float,          # R:R ratio (should be 1.5+)
    "atr": float,
    "stop_pct": float,          # % to SL
    "target_pct": float,        # % to TP
  }
  ```
- **Ratio:** 1.5:1 (2x ATR risk, 3x ATR reward)

---

## 4. SCANNER/__INIT__.PY - Package Exports

**Currently EMPTY** (no exports)

All modules imported directly:
```python
from scanner.data_fetcher import fetch_bulk_data
from scanner.signals import analyze_stock
from scanner.advanced import compute_risk_score, etc.
```

---

## 5. AUTO_SCAN.PY - Scheduled Scan Loop

### Main Scan Flow: `run_scan(shariah: bool, min_price: float, max_price: float, top_n: int) -> Tuple[List[dict], Dict]`
- **Lines 32-67**
- **Returns:** `(results: List[dict], stock_data: Dict[symbol, DataFrame])`
- **Process:**
  1. Fetch all Shariah symbols (line 34)
  2. Bulk download 1-year data (line 35)
  3. For each stock:
     - Compute indicators (line 40)
     - Get latest indicators (line 41)
     - **Price filter:** 0.50-3.00 RM (line 44-48)
     - `analyze_stock(ind)` for signals (line 50)
     - Multi-timeframe bonus (line 53)
     - Volume spike detection (line 56)
  4. Filter: Only STRONG BUY, BUY signals (line 51)
  5. Sort by net_score descending (line 66)
  6. Return top N results (line 67)

### Portfolio Check: `check_portfolio_alerts() -> Tuple[List[dict], List[dict]]`
- **Lines 70-108**
- **Returns:** `(alerts: SELL/STRONG SELL, statuses: all stocks)`
- **For Each Portfolio Stock:**
  - Calculate P/L %: `(current - buy_price) / buy_price`
  - Check if SELL/STRONG SELL signal
  - Store sell_reasons if alert

### Main Flow: `main()`
- **Lines 111-209**
- **Sequence:**
  1. Check market sentiment (line 125-129)
  2. Run scan (line 132-139)
  3. Log new signals (line 142-144)
  4. Update past signal outcomes (line 147-149)
  5. Format scan results (line 151)
  6. Add sentiment + sector rotation + volume spikes (line 154-172)
  7. Check portfolio if requested (line 174-185)
  8. Send via Telegram OR print to console (line 191-206)

### Where Results Are Filtered & Formatted
- **Filter:** Line 51 - only STRONG BUY / BUY pass through
- **Format:** `format_scan_results()` from `telegram_notify.py` (line 151)
- **Sentiment Formatting:** HTML tags for Telegram (line 154-155)
- **Sector Formatting:** Line 158-162

---

## 6. BOT.PY - Telegram Bot

### /scan Command: `handle_scan(chat_id)`
- **Lines 89-139**
- **Flow:**
  1. Fetch all Shariah symbols (line 93)
  2. Bulk download 1y data with 0.2s delay (line 94)
  3. For each stock (line 97-118):
     - Compute indicators
     - Price filter 0.50-3.00 (line 102-103)
     - `analyze_stock(ind)` (line 105)
     - Multi-timeframe bonus (line 106)
     - Volume spike detection (line 110)
     - Add if STRONG BUY or BUY (line 109)
  4. Sort by net_score (line 120)
  5. Format as Telegram HTML (line 126-136)
  6. Show top 15 (line 129)

### /check Command: `handle_check(chat_id, args: str)`
- **Lines 142-235**
- **Detailed Stock Analysis:**
  1. Parse symbol, normalize to .KL format (line 144-150)
  2. Fetch stock data 1y (line 159)
  3. Compute indicators + analyze (line 164-166)
  4. Multi-timeframe score (line 169)
  5. Find support/resistance (line 173)
  6. Detect volume spike (line 176)
  7. Calculate position size (RM 10k capital) (line 179)
  8. Get sector + Shariah status (line 182-183)
  9. Format detailed message with indicators, reasons, S/R, spike, sizing (line 194-235)

### Message Router: `process_message(message: dict)`
- **Lines 402-424**
- **Parses:** Command + arguments
- **Routes:** to COMMANDS dict (line 390-398)
- **Error Handling:** Catches exceptions, replies with error

### Main Loop: `run_once()` or `run_polling()`
- **run_once():** Lines 431-446 - check once, process, exit
- **run_polling():** Lines 449-470 - long-polling loop with 30s timeout

---

## 7. APP.PY - Web Dashboard & Scanner

### Main Scan Engine: `_run_scan(force=False) -> dict`
- **Lines 213-378**
- **Returns:**
  ```python
  {
    "results": List[dict],       # sorted by net_score
    "total": int,
    "failed": int,
    "time": datetime,
    "stock_data": Dict,
    "sentiment": dict,
  }
  ```
- **Process (in detail):**
  1. **Fetch data (line 234):** batch_download 50 at a time
  2. **Sentiment check (line 238):** score adjustment
  3. **For each stock (line 243-296):**
     - Compute indicators
     - Get latest
     - `analyze_stock(ind)`
     - Multi-timeframe bonus + sentiment adjustment (line 250-255)
     - Dividend yield from Dividends column (line 267-270)
     - Risk score (line 280)
     - Volume/Price Analysis (VPA) (line 285-292)
     - **VPA score adjustment** (capped ±15)
  4. **Confirmation checking (line 299-310):**
     - Compare with previous scan signals
     - If stock was BUY both times: confirmed = True
     - Add +10 bonus if confirmed
  5. **Confidence grading (line 313-351):**
     - Compute grade A-F (line 314-324)
     - Detect emerging setups (line 335)
     - Check strategy match (line 345-348)
  6. **Save signals + update outcomes (line 369-372)**
  7. **Cache result + persist to disk (line 366-367)**

### Routes & Formatting

#### `/` Dashboard: `dashboard()`
- **Lines 407-413**
- Returns cached scan + KLCI sentiment + sector data

#### `/scan` Full Scanner: `scan()`
- **Lines 416-429**
- Shows cached OR initiates background scan
- HTMX polling to `/scan/status`

#### `/stock/<symbol>` Detail: `stock_detail(symbol)`
- **Lines 492-559**
- **Detailed Analysis:**
  - All indicators
  - Multi-timeframe score
  - Support/resistance
  - Volume spike
  - Position sizing (RM 10k)
  - Risk score + entry plan
  - VPA analysis
  - Confidence grade
  - Trade summary

#### `/sectors` Sector Rotation: `sectors()`
- **Lines 562-571**
- Uses pre-computed scan results

#### Key Helper: `_build_sector_data(scan) -> List[dict]`
- **Lines 574-630**
- Groups results by sector
- Calculates:
  - Avg score, RSI, 1-month price %
  - Buy/sell counts
  - Top stock per sector
  - Trend emoji

---

## 8. STOCK_HUNTER.PY - CLI Scanner

### Main Commands

#### `cmd_scan(args)` - Scan all stocks
- **Lines 68-167**
- **Flow:**
  1. Get symbols (line 76)
  2. Bulk download 1y (line 77)
  3. For each stock:
     - Compute indicators + analyze (line 87)
     - Multi-timeframe bonus (line 90-91)
     - Volume spike (line 105-106)
     - Store additional fields: symbol, name, close, rsi, adx, volume_ratio, spike
  4. Filter to BUY signals (line 116)
  5. Display as Rich table (line 120-152)

#### `cmd_check(args, capital=10000)` - Check one stock
- **Lines 170-280**
- **Detailed analysis:**
  1. Fetch 1y data (line 179)
  2. Compute indicators + analyze (line 184-186)
  3. Multi-timeframe score (line 240)
  4. Support/resistance (line 246)
  5. Volume spike (line 257)
  6. **Position sizing with capital parameter** (line 265-266)
  7. Display all in Rich format

#### `cmd_portfolio(args)` - Check portfolio
- **Lines 415-502**
- **For each portfolio stock:**
  - Fetch 1y data
  - Compute indicators
  - Check P/L %
  - If SELL/STRONG SELL: flag as alert

#### `cmd_sector(args)` - Sector rotation
#### `cmd_spike(args)` - Volume spikes
#### `cmd_backtest(args)` - Backtest scanner

---

## KEY DATA FLOW DIAGRAM

```
Data Fetcher
├── fetch_bulk_data() / fetch_batch_download()
│   └── Returns: Dict[symbol, DataFrame(OHLCV)]
│
├── fetch_stock_info() [UNUSED IN SCORING]
│   └── Returns: Dict with P/E, Market Cap, Sector, Name
│
Indicators
└── compute_indicators(df)
    └── get_latest_indicators(df)
        └── Returns: Dict with EMA20/50/200, RSI, ADX, MACD, ATR, Volume SMA, etc.

Signals (Main Scoring)
├── analyze_stock(ind)
│   ├── compute_buy_score(ind) → (score, reasons)
│   ├── compute_sell_score(ind) → (score, reasons)
│   ├── classify_signal(buy, sell) → "STRONG BUY" | "BUY" | ... | "STRONG SELL"
│   └── Returns: {buy_score, sell_score, net_score, signal, reasons}
│
Advanced Scoring (Enhancements)
├── multi_timeframe_score(df) → (bonus_score, desc)
├── detect_volume_spike(df) → {...spike_info...} or None
├── compute_risk_score(ind) → {level, points, warnings}
├── compute_confidence_grade(net_score, vol_ratio, mtf_desc, risk, confirmed) → {grade, label, points, factors}
├── detect_emerging_setup(df, ind, net_score, grade) → {...} or None
└── [UNUSED] get_dividend_yield(info) → float or None

Usage Patterns
├── Auto Scan: run_scan() → scan results + format → Telegram
├── CLI: cmd_scan() / cmd_check() → display
├── Web: _run_scan() → cache → dashboard/scanner pages
└── Bot: handle_scan() / handle_check() → format → Telegram reply
```

---

## WHERE TO INJECT FUNDAMENTAL ANALYSIS

### Option 1: Enhance `fetch_stock_info()`
**File:** `scanner/data_fetcher.py` (line 29-42)
- Extend to fetch: P/E, EPS growth, debt/equity, ROE, dividend payout ratio, etc.
- **Challenge:** Yahoo Finance limits on some fields for Malaysian stocks
- **Implementation:**
  ```python
  def fetch_stock_info(symbol: str) -> dict:
      ticker = yf.Ticker(symbol)
      info = ticker.info
      return {
          "pe_ratio": info.get("trailingPE"),
          "eps": info.get("trailingEps"),
          "dividend_yield": info.get("dividendYield"),
          "roa": info.get("returnOnAssets"),
          "roe": info.get("returnOnEquity"),
          "debt_to_equity": info.get("debtToEquity"),
          # Add more...
      }
  ```

### Option 2: Create new `compute_fundamental_score()`
**File:** `scanner/advanced.py`
- Add after `compute_risk_score()` (line 284)
- New function signature:
  ```python
  def compute_fundamental_score(info: dict) -> tuple[int, list[str]]:
      """Score based on P/E, EPS growth, dividend, debt metrics."""
      score = 0
      reasons = []
      
      pe = info.get("pe_ratio")
      if pe and 10 < pe < 20:  # reasonable P/E range
          score += 10
          reasons.append(f"Fair P/E {pe:.1f}")
      
      # ... add more logic
      
      return score, reasons
  ```

### Option 3: Integrate into main `analyze_stock()`
**File:** `scanner/signals.py` (line 231-244)
- Modify to accept optional `info` parameter:
  ```python
  def analyze_stock(ind: dict, info: dict = None) -> dict:
      buy_score, buy_reasons = compute_buy_score(ind)
      sell_score, sell_reasons = compute_sell_score(ind)
      
      # Add fundamental scoring
      if info:
          fund_score, fund_reasons = compute_fundamental_score(info)
          buy_score += max(0, fund_score)  # only positive fundamentals boost
          buy_reasons.extend(fund_reasons)
      
      # ... rest of function
  ```

### Option 4: Integrate Dividend Yield into Scoring
**File:** `scanner/advanced.py` (line 156-158)
- Currently `get_dividend_yield()` is unused
- **Create scoring function:**
  ```python
  def score_dividend_yield(div_yield: float, current_price: float) -> tuple[int, str]:
      """Score stocks based on dividend yield."""
      if div_yield is None or div_yield <= 0:
          return 0, ""
      
      if div_yield >= 5.0:  # high yield
          return 10, f"High dividend yield {div_yield:.2f}%"
      elif div_yield >= 3.0:
          return 5, f"Good dividend yield {div_yield:.2f}%"
      return 0, ""
  ```

---

## BEST INJECTION POINTS (Ranked by Impact)

### 🥇 **Priority 1: Modify `_run_scan()` in app.py** (Line 213-378)
- **Where:** Between line 248-256 (after analyze_stock, before MTF bonus)
- **What to add:**
  ```python
  # Fetch fundamental data
  fund_info = fetch_stock_info(symbol)  # enhance to return more fields
  
  # Compute fundamental score
  fund_score, fund_reasons = compute_fundamental_score(fund_info)
  
  # Add to analysis
  analysis["fundamental_score"] = fund_score
  analysis["buy_reasons"].extend(fund_reasons)
  analysis["net_score"] += fund_score
  analysis["fund_info"] = fund_info
  ```
- **Impact:** Affects all web scans, dashboards, and signal logging

### 🥈 **Priority 2: Enhance `run_scan()` in auto_scan.py** (Line 32-67)
- **Where:** Similar insertion point as above
- **Impact:** Affects scheduled Telegram scans

### 🥉 **Priority 3: Extend `analyze_stock()` in signals.py** (Line 231-244)
- **Make it truly modular:** Accept optional `info` dict
- **Impact:** Simplifies all calling code

### 4️⃣ **Priority 4: Create fundamental module**
- **New file:** `scanner/fundamentals.py`
- **Functions:**
  - `fetch_fundamental_data(symbol: str) -> dict`
  - `compute_fundamental_score(info: dict) -> tuple[int, list[str]]`
  - `score_pe_ratio(pe: float) -> tuple[int, str]`
  - `score_dividend_yield(div: float) -> tuple[int, str]`
  - etc.

---

## CURRENT DIVIDEND YIELD USAGE

**Only place dividend data is used:**
- **app.py line 267-268:**
  ```python
  div_total = df["Dividends"].sum() if "Dividends" in df.columns else 0
  analysis["div_yield"] = (div_total / ind["close"] * 100) if ind["close"] > 0 and div_total > 0 else 0
  ```
- **Problem:** Checks historical 1y dividends on DataFrame, not current dividend yield
- **Better:** Use info from Yahoo's `.info` dictionary

---

## SUMMARY TABLE

| Component | File | Function | Input | Output | Used For |
|-----------|------|----------|-------|--------|----------|
| Data Fetch | data_fetcher.py | fetch_bulk_data | symbols | Dict[symbol, DF] | All scans |
| Stock Info | data_fetcher.py | fetch_stock_info | symbol | {pe, cap, sector} | **UNUSED** ⚠️ |
| Indicators | indicators.py | compute_indicators | DF | DF with cols | All analysis |
| Latest Ind | indicators.py | get_latest_indicators | DF | Dict{close, EMA, RSI, ...} | Signal scoring |
| Buy Score | signals.py | compute_buy_score | ind dict | (score, reasons) | analyze_stock |
| Sell Score | signals.py | compute_sell_score | ind dict | (score, reasons) | analyze_stock |
| Analyze | signals.py | analyze_stock | ind dict | {signal, scores, reasons} | **CORE** |
| MTF Score | advanced.py | multi_timeframe_score | DF | (bonus, desc) | All scans |
| Risk | advanced.py | compute_risk_score | ind dict | {level, points, warnings} | app.py |
| Grade | advanced.py | compute_confidence_grade | net_score, vol, mtf, risk, confirmed | {grade A-F, points, factors} | app.py |
| Emerging | advanced.py | detect_emerging_setup | df, ind, score, grade | {is_emerging, points, reasons} | app.py |
| Entry Plan | advanced.py | calculate_entry_plan | close, atr | {SL, TP, RR ratio} | stock detail |
| Position Size | advanced.py | calculate_position_size | capital, price, SL% | {lots, shares, amount, risk} | All detail pages |

