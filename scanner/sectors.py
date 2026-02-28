"""
Sector rotation analysis — identify which sectors are trending up/down.
"""

import pandas as pd
from typing import Dict, List, Tuple

from scanner.symbols import SYMBOLS
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock


# Map each stock to its sector
SECTOR_MAP = {
    # Banking & Finance
    "1155.KL": "Banking", "1295.KL": "Banking", "6888.KL": "Banking",
    "5819.KL": "Banking", "1066.KL": "Banking", "5185.KL": "Banking",
    "8583.KL": "Banking", "5053.KL": "Banking", "1023.KL": "Banking",
    "5258.KL": "Banking", "6947.KL": "Finance", "5291.KL": "Finance",
    "1818.KL": "Finance", "6012.KL": "Finance", "1015.KL": "Finance",
    "2488.KL": "Banking", "1082.KL": "Banking", "5139.KL": "Finance",
    "1163.KL": "Finance", "8621.KL": "Finance", "1058.KL": "Finance",
    "1171.KL": "Finance",

    # Plantation
    "5285.KL": "Plantation", "2445.KL": "Plantation", "1961.KL": "Plantation",
    "2291.KL": "Plantation", "2054.KL": "Plantation", "5113.KL": "Plantation",
    "5126.KL": "Plantation", "2852.KL": "Plantation",
    "5138.KL": "Plantation", "5012.KL": "Plantation",

    # Technology
    "0166.KL": "Technology", "0023.KL": "Technology", "5264.KL": "Technology",
    "0042.KL": "Technology", "0072.KL": "Technology", "0180.KL": "Technology",
    "5318.KL": "Technology", "0041.KL": "Technology", "0078.KL": "Technology",
    "0053.KL": "Technology", "0005.KL": "Technology", "0160.KL": "Technology",
    "0173.KL": "Technology", "0200.KL": "Technology",
    "0128.KL": "Technology", "5005.KL": "Technology", "7204.KL": "Technology",
    "7022.KL": "Technology", "5286.KL": "Technology", "0090.KL": "Technology",
    "7160.KL": "Technology", "0208.KL": "Technology", "7100.KL": "Technology",
    "9334.KL": "Technology", "4456.KL": "Technology", "5216.KL": "Technology",
    "8176.KL": "Technology", "3816.KL": "Technology",

    # Construction
    "5398.KL": "Construction", "3336.KL": "Construction", "5222.KL": "Construction",
    "8206.KL": "Construction", "5032.KL": "Construction", "1546.KL": "Construction",
    "5161.KL": "Construction", "8893.KL": "Construction", "5027.KL": "Construction",
    "9679.KL": "Construction", "5263.KL": "Construction", "8877.KL": "Construction",
    "5703.KL": "Construction", "3204.KL": "Construction",
    "5984.KL": "Construction", "1538.KL": "Construction", "5237.KL": "Construction",

    # Property & REIT
    "1724.KL": "Property", "5148.KL": "Property", "8664.KL": "Property",
    "5168.KL": "Property", "1651.KL": "Property", "5202.KL": "Property",
    "1771.KL": "Property", "5227.KL": "REIT", "5106.KL": "REIT",
    "5183.KL": "REIT", "5212.KL": "REIT", "5180.KL": "REIT",
    "5235.KL": "REIT",
    "5249.KL": "Property", "5211.KL": "Property", "5176.KL": "REIT",
    "5235SS.KL": "REIT", "5123.KL": "REIT",
    "8567.KL": "Property", "1562.KL": "Property", "7183.KL": "Property",
    "5231.KL": "Property", "5200.KL": "Property",

    # Consumer & Healthcare
    "4715.KL": "Consumer", "3689.KL": "Consumer", "4707.KL": "Consumer",
    "2658.KL": "Consumer", "3255.KL": "Consumer", "6399.KL": "Consumer",
    "5296.KL": "Consumer", "6556.KL": "Consumer", "5109.KL": "Consumer",
    "5225.KL": "Healthcare", "7113.KL": "Healthcare", "7153.KL": "Healthcare",
    "7084.KL": "Healthcare", "5347.KL": "Healthcare", "7103.KL": "Healthcare",
    "9296.KL": "Healthcare", "7106.KL": "Healthcare", "7090.KL": "Healthcare",
    "6963.KL": "Healthcare",
    "7052.KL": "Consumer", "6599.KL": "Consumer", "5275.KL": "Consumer",
    "2127.KL": "Consumer", "3026.KL": "Consumer", "2836.KL": "Consumer",
    "5291.KL": "Consumer", "4818.KL": "Consumer", "3743.KL": "Consumer",
    "5141.KL": "Consumer", "5239.KL": "Consumer", "5292.KL": "Consumer",
    "7129.KL": "Consumer", "5247.KL": "Consumer",

    # Energy
    "5681.KL": "Energy", "6033.KL": "Energy", "5783.KL": "Energy",
    "5218.KL": "Energy", "5182.KL": "Energy", "5279.KL": "Energy",
    "5243.KL": "Energy", "2577.KL": "Energy", "5125.KL": "Energy",
    "5186.KL": "Energy",
    "7277.KL": "Energy", "7293.KL": "Energy", "7250.KL": "Energy",
    "5210.KL": "Energy", "5199.KL": "Energy",

    # Telecom & Utilities
    "4863.KL": "Telecom", "4818.KL": "Telecom", "3867.KL": "Telecom",
    "6742.KL": "Utilities", "8524.KL": "Utilities", "3794.KL": "Utilities",
    "4677.KL": "Utilities", "5264.KL": "Utilities", "5272.KL": "Utilities",
    "5209.KL": "Utilities", "6888.KL": "Telecom", "6947.KL": "Telecom",
    "6012.KL": "Telecom",

    # Industrial
    "3158.KL": "Industrial", "5014.KL": "Industrial", "4065.KL": "Industrial",
    "2828.KL": "Industrial", "7087.KL": "Industrial", "4197.KL": "Industrial",
    "8052.KL": "Industrial", "5200.KL": "Industrial", "7277.KL": "Industrial",
    "8869.KL": "Industrial", "5246.KL": "Industrial", "7155.KL": "Industrial",
    "4731.KL": "Industrial", "7148.KL": "Industrial", "7773.KL": "Industrial",
    "7164.KL": "Industrial", "6139.KL": "Industrial", "9601.KL": "Industrial",
    "7191.KL": "Industrial", "7076.KL": "Industrial", "6645.KL": "Industrial",
    "5300.KL": "Industrial",

    # Diversified
    "3182.KL": "Gaming", "2267.KL": "Diversified", "1562.KL": "Consumer",
    "6076.KL": "Consumer", "2488.KL": "Consumer", "8567.KL": "Industrial",
    "3395.KL": "Diversified", "5196.KL": "Diversified", "5024.KL": "Diversified",
    "7237.KL": "Diversified", "7081.KL": "Healthcare", "7216.KL": "Diversified",
    "4588.KL": "Diversified", "3417.KL": "Diversified", "5020.KL": "Diversified",
    "5053.KL": "Diversified",

    # ACE Market
    "0004.KL": "Technology", "0176.KL": "Technology", "0120.KL": "Property",
    "0012.KL": "Telecom", "0097.KL": "Technology", "0150.KL": "Technology",
    "0152.KL": "Technology", "0185.KL": "Energy", "0138.KL": "Consumer",
    "0082.KL": "Technology", "0051.KL": "Technology", "0020.KL": "Technology",
    "0049.KL": "Industrial",
    "1368.KL": "Technology",

    # New additions
    "0195.KL": "Technology", "0223.KL": "Healthcare", "0216.KL": "Technology",
    "0240.KL": "Utilities", "0191.KL": "Technology", "0155.KL": "Construction",
    "0171.KL": "Technology", "0058.KL": "Utilities",
    "9695.KL": "Industrial", "9172.KL": "Industrial", "6165.KL": "Property",
    "5059.KL": "Industrial", "7839.KL": "Industrial",
    "4383.KL": "Industrial", "8354.KL": "Industrial", "6688.KL": "Technology",
    "7161.KL": "Technology", "0033.KL": "Technology", "0109.KL": "Consumer",
    "0116.KL": "Construction", "0014.KL": "Consumer", "0039.KL": "Technology",
    "6823.KL": "Construction", "9253.KL": "Finance",
    "0091.KL": "Technology", "0118.KL": "Technology", "0146.KL": "Technology",
    "0187.KL": "Energy", "0198.KL": "Consumer", "0201.KL": "Industrial",
    "0207.KL": "Technology", "0235.KL": "Construction",
    "1538.KL": "Construction", "2070.KL": "Industrial",
    "3239.KL": "Consumer", "3948.KL": "Industrial",
    "5002.KL": "Industrial", "5021.KL": "Technology",
    "5099.KL": "Consumer", "5142.KL": "Industrial",
    "5213.KL": "Finance", "6432.KL": "Construction",
    "7048.KL": "Industrial", "7088.KL": "Industrial",
    "7120.KL": "Industrial", "7230.KL": "Technology",
    "7471.KL": "Technology", "7668.KL": "Industrial",
    "5202.KL": "Consumer", "7183.KL": "Property",
}


def get_sector(symbol: str) -> str:
    """Get sector for a stock symbol."""
    return SECTOR_MAP.get(symbol, "Others")


def analyze_sectors(stock_data: Dict[str, pd.DataFrame]) -> List[dict]:
    """
    Analyze sector performance and momentum.
    Returns list of sector dicts sorted by strength.
    """
    sector_stocks = {}  # sector -> list of (symbol, indicators)

    for symbol, df in stock_data.items():
        sector = get_sector(symbol)
        try:
            df = compute_indicators(df)
            ind = get_latest_indicators(df)
            if ind.get("close") is None:
                continue

            analysis = analyze_stock(ind)

            # Calculate price change %
            if len(df) >= 20:
                pct_1m = ((ind["close"] - df.iloc[-20]["Close"]) / df.iloc[-20]["Close"]) * 100
            else:
                pct_1m = 0

            if sector not in sector_stocks:
                sector_stocks[sector] = []
            sector_stocks[sector].append({
                "symbol": symbol,
                "close": ind["close"],
                "rsi": ind.get("rsi", 50),
                "adx": ind.get("adx", 0),
                "signal": analysis["signal"],
                "net_score": analysis["net_score"],
                "pct_1m": pct_1m,
            })
        except Exception:
            continue

    # Aggregate per sector
    results = []
    for sector, stocks in sector_stocks.items():
        if not stocks:
            continue

        avg_score = sum(s["net_score"] for s in stocks) / len(stocks)
        avg_rsi = sum(s["rsi"] for s in stocks) / len(stocks)
        avg_pct = sum(s["pct_1m"] for s in stocks) / len(stocks)
        buy_count = sum(1 for s in stocks if s["signal"] in ("BUY", "STRONG BUY"))
        sell_count = sum(1 for s in stocks if s["signal"] in ("SELL", "STRONG SELL"))

        if avg_score >= 30:
            trend = "🟢 HOT"
        elif avg_score >= 10:
            trend = "🟡 WARM"
        elif avg_score >= -10:
            trend = "⚪ NEUTRAL"
        else:
            trend = "🔴 COLD"

        results.append({
            "sector": sector,
            "trend": trend,
            "avg_score": avg_score,
            "avg_rsi": avg_rsi,
            "avg_pct_1m": avg_pct,
            "stock_count": len(stocks),
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "top_stock": max(stocks, key=lambda s: s["net_score"]),
        })

    results.sort(key=lambda x: x["avg_score"], reverse=True)
    return results
