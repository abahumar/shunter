# Stock Hunter Webapp Design

## Overview
Add a web interface to Stock Hunter using Flask + HTMX + Tailwind CSS + TradingView Lightweight Charts. Personal use, runs locally. Existing CLI and Telegram bot remain untouched.

## Architecture
- Flask serves HTML partials (HTMX) and JSON (charts)
- Jinja2 templates with Tailwind CSS via CDN
- Lightweight Charts via CDN for interactive candlestick charts
- In-memory cache (dict with TTL) to avoid repeated Yahoo Finance fetches
- Existing `scanner/` module called directly — zero rewriting

## Pages
1. **Dashboard** (`/`) — Summary cards, top 5 picks, sector heatmap, recent spikes
2. **Scanner** (`/scan`) — Full scan table, sortable, filterable by signal type
3. **Stock Detail** (`/stock/<symbol>`) — Candlestick chart + EMA/Bollinger/volume overlays, indicators, S/R levels, position sizing, buy/sell reasons
4. **Sectors** (`/sectors`) — Sector rotation table (HOT/WARM/COLD), drill-down
5. **Volume Spikes** (`/spikes`) — Spike table with bullish/bearish classification
6. **Portfolio** (`/portfolio`) — Holdings, P&L, sell alerts, add/remove form
7. **Signal Tracker** (`/tracker`) — Historical signal win rate, avg return, outcomes

## API Routes (JSON)
- `GET /api/chart/<symbol>` — OHLCV + indicator series for Lightweight Charts
- `GET /api/search?q=` — Stock search autocomplete

## Caching
- Scan results: 15 min TTL
- Individual stock: 10 min TTL
- Portfolio: no cache
- Manual refresh button to bypass cache

## Theme
Dark (Bloomberg-style). Slate backgrounds, green/red signals, blue accents.

## New Files
- `app.py` — Flask entry point
- `templates/base.html` — Shell with sidebar
- `templates/dashboard.html`
- `templates/scanner.html`
- `templates/stock_detail.html`
- `templates/sectors.html`
- `templates/spikes.html`
- `templates/portfolio.html`
- `templates/tracker.html`
- `static/app.js` — Chart init + HTMX hooks

## Dependencies
- `flask` (added to requirements.txt)
- Tailwind CSS via CDN
- Lightweight Charts via CDN
- HTMX via CDN
