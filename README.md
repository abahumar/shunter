# 🎯 Stock Hunter - Bursa Malaysia Stock Scanner

A Python CLI tool that scans **all Bursa Malaysia stocks** and recommends **BUY/SELL signals** for medium to long-term traders using technical analysis.

## Features

- 📊 **Full market scan** - Scans 150+ Bursa Malaysia stocks
- 🟢 **BUY signals** - Ranks stocks by multi-indicator scoring
- 🔴 **SELL alerts** - Monitors your portfolio for exit signals
- 📈 **Technical analysis** - EMA, MACD, RSI, ADX, Volume, Bollinger Bands
- 💰 **Portfolio tracker** - Track your bought stocks and get sell alerts
- 🆓 **Free data** - Uses Yahoo Finance (no API key needed)

## Installation

```bash
# Clone or download this project
cd Stock-hunter

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Scan the market for BUY signals

```bash
python stock_hunter.py scan              # Scan all stocks
python stock_hunter.py scan --top 10     # Show top 10 only
```

### Check a specific stock

```bash
python stock_hunter.py check 1155.KL     # Check Maybank
python stock_hunter.py check 5398        # Also works without .KL
```

### Portfolio management

```bash
# Add stocks you've bought
python stock_hunter.py add 1155.KL 8.50
python stock_hunter.py add 5398.KL 4.20 --quantity 1000

# Check if any should be sold
python stock_hunter.py portfolio

# List your portfolio
python stock_hunter.py list

# Remove a stock
python stock_hunter.py remove 1155.KL
```

### Search for stocks

```bash
python stock_hunter.py search maybank
python stock_hunter.py search 1155
```

## How It Works

### Signal Scoring System

Each stock is scored based on multiple technical indicators:

| Indicator | BUY Signal | SELL Signal |
|-----------|-----------|-------------|
| **EMA Trend** | Price > EMA50 > EMA200 (+20) | Price < EMA50 < EMA200 (-20) |
| **MACD** | Bullish crossover (+15) | Bearish crossover (-15) |
| **RSI** | 40-65 range (+15) | Above 75 (-15) |
| **ADX** | > 25 with DI+ > DI- (+15) | > 25 with DI- > DI+ (-15) |
| **Volume** | Above 1.5x average (+15) | OBV declining (-5) |
| **52-Week** | Near low (value) (+5) | Near high (resistance) (-10) |
| **Bollinger** | Near lower band (+5) | Near upper band (-5) |

### Signal Classification

| Score | Signal |
|-------|--------|
| ≥ 60 | 🟢 STRONG BUY |
| ≥ 35 | 🟢 BUY |
| ≥ 10 | 🟡 WATCH |
| ≥ -20 | ⚪ HOLD |
| ≥ -45 | 🔴 SELL |
| < -45 | 🔴 STRONG SELL |

## 🤖 Auto Alerts (Telegram + GitHub Actions)

Run the scanner automatically every weekday and get results on your phone — **FREE, no server needed**.

### Step 1: Create Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot` → name it "Stock Hunter Alert"
3. Copy the **bot token** (looks like `123456:ABC-DEF...`)
4. Open your new bot and send `/start`
5. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
6. Copy your **chat_id** number from the response

### Step 2: Push to GitHub

```bash
cd Stock-hunter
git init
git add .
git commit -m "Stock Hunter scanner"
gh repo create Stock-hunter --private --push
```

### Step 3: Add Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Name | Value |
|------------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from Step 1 |
| `TELEGRAM_CHAT_ID` | Your chat ID from Step 1 |

### Step 4: Done! 🎉

The scanner runs **every weekday at 5:30 PM MYT** automatically. You'll get a Telegram message like:

```
🎯 Stock Hunter - ☪ Shariah Scan
📊 Found 15 BUY signals

🟢 #1 5258.KL — MBSB
   RM 2.54 | Score: 65 | STRONG BUY
🔵 #2 7277.KL — Dialog
   RM 1.76 | Score: 60 | BUY
...
```

To trigger a manual scan: Go to **Actions** tab → **Stock Hunter Daily Scan** → **Run workflow**

## ⚠️ Disclaimer

This tool is for **educational and informational purposes only**. It is NOT financial advice. Always do your own research and consult a licensed financial advisor before making investment decisions. Past performance does not guarantee future results. Trading stocks involves risk of loss.

## License

MIT
