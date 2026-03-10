# 🚀 Stock Hunter — Improvement Roadmap

> Ideas to help users make decisions more confidently and minimize risk.

---

## 🔴 High Priority — Decision Confidence & Risk

### 1. Chart Pattern Detection
Automatically detect classic price patterns that signal breakouts or reversals.
- **Patterns:** Double Bottom, Cup & Handle, Head & Shoulders, Ascending Triangle, Breakout from Resistance
- **Impact:** Adds visual confirmation layer on top of indicator-based scoring
- **Where:** New `scanner/patterns.py` module, badge in scanner table, overlay on stock detail chart

### 2. Price Alert System
Notify the user when a watchlist stock hits a key level (support/resistance break, ATR-based target).
- **Trigger:** Support break, resistance breakout, ATR stop-loss hit, custom price level
- **Delivery:** Telegram push notification + alert badge in watchlist
- **Impact:** Users don't need to constantly check the app

### 3. Portfolio Equity Curve
Show portfolio value over time as a line chart on the Portfolio page.
- **Track:** Daily portfolio value snapshot (sum of holdings × current price)
- **Display:** Lightweight Charts line chart with drawdown shading
- **Impact:** Users see if their overall strategy is growing or shrinking

### 4. Dividend Filter & Yield Screening
Filter scanner results by dividend yield (e.g., >4%).
- **Data:** Yahoo Finance `dividendYield` field
- **Display:** Div Yield column in scanner, "💰 High Yield" filter button
- **Impact:** Income-focused investors can filter for steady dividend payers

### 5. Transaction History & Trade Journal
Record every buy/sell action with entry/exit price, P&L, and notes.
- **Storage:** New `transactions` table in SQLite
- **Display:** Timeline view per stock showing all trades
- **Impact:** Users learn from past trades — which setups worked, which didn't

---

## 🟡 Medium Priority — Smarter Analysis

### 6. Foreign Fund Flow Indicator
Track institutional buying/selling pressure using volume-at-price analysis.
- **Method:** Compare current volume vs 20-day average at specific price levels
- **Display:** "Smart Money: Accumulating / Distributing" badge
- **Impact:** Aligns with VPA — confirms whether big players are entering or exiting

### 7. Screener Presets (Quick Filters)
One-click filter presets for common strategies.
- **Presets:** Growth (high ADX + rising EMA), Income (high dividend + low risk), Momentum (high score + volume spike), Value (low P/E + BUY signal)
- **Display:** Dropdown or button group above scanner table
- **Impact:** Beginners don't need to understand all indicators — just pick a strategy

### 8. Weekly Performance Report
Auto-generated summary comparing last week's signals to this week's outcomes.
- **Content:** "Last week's BUY picks: average +2.3%", best/worst performer, hit rate
- **Delivery:** Dashboard card + optional Telegram summary
- **Impact:** Builds confidence over time by showing track record

### 9. Relative Strength Ranking
Rank all scanned stocks by price performance relative to KLCI.
- **Method:** (Stock return - KLCI return) over 1-week, 1-month, 3-month windows
- **Display:** RS column in scanner, sort by strongest relative performer
- **Impact:** Finds stocks that outperform the market — momentum leaders

### 10. Correlation Matrix for Portfolio
Show which portfolio holdings move together.
- **Method:** 60-day price correlation between all held stocks
- **Display:** Heatmap on Portfolio page (red = highly correlated, green = diversified)
- **Impact:** Prevents overconcentration — if 3 stocks correlate 0.9+, you're betting on the same thing

---

## 🟢 Nice to Have — UX & Automation

### 11. Stock Comparison Tool
Side-by-side comparison of 2-3 stocks on all indicators.
- **Display:** Multi-column table or overlay chart with synchronized timescale
- **Impact:** Helps decide between similar candidates (e.g., two bank stocks)

### 12. Earnings Calendar Integration
Show upcoming earnings dates for watchlist/portfolio stocks.
- **Data:** Yahoo Finance earnings dates
- **Display:** Calendar widget on Dashboard, ⚠️ badge on stocks reporting this week
- **Impact:** Avoid buying before earnings (high volatility risk) or plan around it

### 13. Mobile-Responsive Improvements
Optimize scanner table and charts for phone screens.
- **Changes:** Collapsible columns, swipe navigation, bottom tab bar
- **Impact:** Most Bursa retail investors check stocks on phones during commute

### 14. Export to CSV/PDF
Export scan results, portfolio, or backtest results as downloadable files.
- **Formats:** CSV for spreadsheet analysis, PDF for record-keeping
- **Impact:** Users who want to analyze offline or share with remisiers

### 15. Dark/Light Theme Toggle
Currently dark theme only — add a light mode option.
- **Method:** CSS variables swap via toggle button
- **Impact:** Usability preference — some users prefer light backgrounds

### 16. Backtest Comparison Mode
Run two backtest configurations side by side and compare metrics.
- **Display:** Split-panel showing Strategy A vs Strategy B (win rate, profit, drawdown)
- **Impact:** Users can empirically test which strategy works better

### 17. Scanner History Timeline
Store scan results daily and show how signals evolve over time per stock.
- **Display:** "This stock was BUY 3 days in a row" or "Flipped from SELL to BUY today"
- **Impact:** Signal persistence is a strong confidence indicator (already partially tracked via consecutive confirmation)

### 18. Notification Preferences
Let users configure which alerts they want (Telegram, browser push, email).
- **Settings:** Per-alert-type toggles (scan complete, sell alert, price alert, weekly report)
- **Impact:** Reduces noise — only get alerts that matter to you

### 19. Stock Screener by Financial Metrics
Filter by fundamental data: P/E ratio, market cap, ROE, debt-to-equity.
- **Data:** Yahoo Finance `.info` endpoint
- **Display:** Expandable filter panel above scanner
- **Impact:** Combines technical + fundamental analysis for better quality picks

### 20. AI-Powered Trade Summary
Natural language summary of why a stock is a BUY/SELL, written like a market analyst report.
- **Method:** Template-based text generation using indicator values and patterns
- **Example:** "MAYBANK (1155.KL) — Strong BUY. Price is above all EMAs with rising ADX (32). VPA shows accumulation over 3 days. RSI at 58 gives room to run. Risk: Low. Entry RM 9.45, Stop RM 9.10, Target RM 10.05."
- **Impact:** Beginners who can't interpret raw numbers get a clear, actionable narrative

---

## 📊 Priority Matrix

| # | Feature | Effort | Impact | Priority |
|---|---------|--------|--------|----------|
| 1 | Chart Pattern Detection | High | High | 🔴 |
| 2 | Price Alert System | Medium | High | 🔴 |
| 3 | Portfolio Equity Curve | Medium | High | 🔴 |
| 4 | Dividend Filter | Low | Medium | 🔴 |
| 5 | Transaction History | Medium | High | 🔴 |
| 6 | Fund Flow Indicator | High | Medium | 🟡 |
| 7 | Screener Presets | Low | High | 🟡 |
| 8 | Weekly Report | Medium | Medium | 🟡 |
| 9 | Relative Strength | Low | Medium | 🟡 |
| 10 | Correlation Matrix | Medium | Medium | 🟡 |
| 11 | Stock Comparison | Medium | Medium | 🟢 |
| 12 | Earnings Calendar | Low | Medium | 🟢 |
| 13 | Mobile Responsive | Medium | High | 🟢 |
| 14 | Export CSV/PDF | Low | Low | 🟢 |
| 15 | Dark/Light Theme | Low | Low | 🟢 |
| 16 | Backtest Comparison | Medium | Medium | 🟢 |
| 17 | Scanner History | Medium | Medium | 🟢 |
| 18 | Notification Prefs | Low | Low | 🟢 |
| 19 | Fundamental Screener | Medium | Medium | 🟢 |
| 20 | AI Trade Summary | Low | High | 🟢 |
