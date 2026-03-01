# 🎯 Stock Hunter - Suggested Features

## 🔥 High Impact

- [x] **Sector Rotation** — `python stock_hunter.py sector --shariah` — Shows hot/cold sectors
- [x] **Risk Sizing** — `python stock_hunter.py check SYMBOL --capital 10000` — Position sizing per stock
- [ ] **Dividend Filter** — Flag stocks with high dividend yield (>4%). Extra income while holding long-term.
- [ ] **Earnings Calendar** — Alert before quarterly earnings announcements.

## 📊 Better Signals

- [x] **Multi-timeframe Confirmation** — Weekly + daily both checked in scan & check commands
- [x] **Support/Resistance Levels** — `check` command now shows key price levels
- [x] **Trailing Stop-Loss** — `python stock_hunter.py backtest --trailing-stop` — Dynamic stop
- [x] **Volume Spike Detector** — `python stock_hunter.py spike --shariah` — Unusual volume alerts

## 📱 Better Alerts

- [ ] **Weekly Performance Report** — Every Sunday: "Your picks this week: 3 up, 1 down, +4.2% overall"
- [ ] **Price Target Alerts** — "MBSB hit your target RM 2.80 — consider taking profit"
- [x] **Market Sentiment** — KLCI index trend — is the overall market bullish or bearish?

## 🧠 Advanced

- [x] **Consecutive Signal Confirmation** — BUY must appear in 2+ consecutive scans for +10 bonus (reduces false positives)
- [ ] **Pattern Detection** — Detect chart patterns (double bottom, breakout, cup & handle).
- [ ] **Foreign Fund Flow** — Track if foreign investors are buying/selling Malaysian stocks.
- [ ] **Screener Presets** — Quick commands like `scan --growth`, `scan --dividend`, `scan --momentum`.
