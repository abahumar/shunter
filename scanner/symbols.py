"""
Bursa Malaysia stock symbols list.
Tickers use the .KL suffix on Yahoo Finance (e.g., 1155.KL = Maybank).
"""

# Top actively traded Bursa Malaysia stocks across Main Market & ACE Market.
# Grouped by sector for reference. All use Yahoo Finance .KL suffix.
# Every code verified via yfinance (July 2025).

SYMBOLS = {
    # ── Banking & Finance ──
    "1155.KL": "Maybank",
    "1295.KL": "Public Bank",
    "1023.KL": "CIMB Group",
    "5819.KL": "Hong Leong Bank",
    "1066.KL": "RHB Bank",
    "1015.KL": "AMMB Holdings",
    "2488.KL": "Alliance Bank",
    "1082.KL": "Hong Leong Financial",
    "5185.KL": "AFFIN Bank",
    "5258.KL": "BIMB Holdings",
    "1171.KL": "MBSB",
    "1818.KL": "Bursa Malaysia",
    "1163.KL": "Allianz Malaysia",
    "8621.KL": "LPI Capital",
    "1058.KL": "Manulife",
    "5139.KL": "AEON Credit",

    # ── Plantation ──
    "5285.KL": "SD Guthrie",              # formerly Sime Darby Plantation
    "2445.KL": "KLK",
    "1961.KL": "IOI Corp",
    "2291.KL": "Genting Plantations",
    "5138.KL": "Hap Seng Plantations",
    "5012.KL": "Ta Ann Holdings",

    # ── Technology ──
    "0166.KL": "Inari Amertron",
    "0097.KL": "Vitrox",
    "0128.KL": "Frontken",
    "5005.KL": "Unisem",
    "7204.KL": "D&O Green Technologies",
    "7022.KL": "Globetronics",
    "5286.KL": "MI Technovation",
    "0090.KL": "Elsoft Research",
    "7160.KL": "Pentamaster",
    "0208.KL": "Greatech Technology",
    "7100.KL": "Uchi Technologies",
    "9334.KL": "KESM Industries",
    "3867.KL": "MPI",
    "4456.KL": "Dagang NeXchange",
    "0138.KL": "Zetrix AI",               # formerly MyEG Services
    "5216.KL": "NEXG",                     # formerly Datasonic
    "1368.KL": "UEM Edgenta",

    # ── Construction & Infrastructure ──
    "5398.KL": "Gamuda",
    "3336.KL": "IJM Corp",
    "9679.KL": "WCT Holdings",
    "1651.KL": "MRCB",
    "5263.KL": "Sunway Construction",
    "8877.KL": "Ekovest",
    "5703.KL": "Muhibbah Engineering",
    "0185.KL": "HSS Engineers",
    "3204.KL": "George Kent",

    # ── Property & REIT ──
    "8664.KL": "SP Setia",
    "5249.KL": "IOI Properties",
    "8206.KL": "Eco World Development",
    "5200.KL": "UOA Development",
    "8583.KL": "Mah Sing Group",
    "5211.KL": "Sunway Bhd",
    "5227.KL": "IGB REIT",
    "5212.KL": "Pavilion REIT",
    "5106.KL": "Axis REIT",
    "5176.KL": "Sunway REIT",
    "5235SS.KL": "KLCCP Stapled",
    "5123.KL": "Sentral REIT",
    "5180.KL": "CapitaLand Malaysia Trust",

    # ── Consumer & Retail ──
    "4707.KL": "Nestle Malaysia",
    "3689.KL": "Fraser & Neave",
    "3026.KL": "Dutch Lady",
    "3255.KL": "Heineken Malaysia",
    "2836.KL": "Carlsberg Brewery",
    "5225.KL": "IHH Healthcare",
    "7084.KL": "QL Resources",
    "7113.KL": "Top Glove",
    "7153.KL": "Kossan Rubber",
    "5168.KL": "Hartalega",
    "7106.KL": "Supermax",
    "2127.KL": "Comfort Gloves",
    "7052.KL": "Padini Holdings",
    "6599.KL": "AEON Co",
    "5296.KL": "Mr DIY Group",
    "5275.KL": "MyNews Holdings",

    # ── Oil & Gas / Energy ──
    "5183.KL": "Petronas Chemicals",
    "6033.KL": "Petronas Gas",
    "5681.KL": "Petronas Dagangan",
    "5218.KL": "Vantris Energy",           # formerly Sapura Energy
    "7277.KL": "Dialog Group",
    "7293.KL": "Yinson Holdings",
    "7250.KL": "Uzma",
    "5210.KL": "Bumi Armada",
    "5199.KL": "Hibiscus Petroleum",
    "5243.KL": "Velesto Energy",

    # ── Telecommunications ──
    "6888.KL": "Axiata Group",
    "6947.KL": "CelcomDigi",
    "6012.KL": "Maxis",
    "4863.KL": "Telekom Malaysia",

    # ── Utilities ──
    "5347.KL": "Tenaga Nasional",
    "6742.KL": "YTL Power",
    "4677.KL": "YTL Corporation",
    "5264.KL": "Malakoff",
    "8524.KL": "Taliworks",
    "5272.KL": "Ranhill Utilities",

    # ── Industrial / Manufacturing ──
    "8869.KL": "Press Metal",
    "4065.KL": "PPB Group",
    "5246.KL": "Westports Holdings",
    "7155.KL": "SKP Resources",
    "4731.KL": "Scientex",
    "7148.KL": "Duopharma Biotech",
    "5247.KL": "Karex",
    "7773.KL": "EP Manufacturing",
    "4197.KL": "Sime Darby",

    # ── Diversified / Others ──
    "3182.KL": "Genting Bhd",
    "4715.KL": "Genting Malaysia",
    "3395.KL": "Berjaya Corp",
    "5196.KL": "Berjaya Food",
    "5024.KL": "Hup Seng Industries",
    "7237.KL": "Power Root",
    "7090.KL": "Apex Healthcare",
    "7081.KL": "Pharmaniaga",
    "7216.KL": "Kawan Food",

    # ── ACE Market ──
    "0200.KL": "Revenue Group",
    "0082.KL": "Green Packet",
    "0051.KL": "Cuscapi",
    "0020.KL": "Netx Holdings",
    "0049.KL": "Oceancash Pacific",
}


# ── Non-Shariah compliant stocks ──
# Based on Securities Commission Malaysia Shariah Advisory Council rulings.
# Conventional banks, breweries, gaming, liquor, and insurance (conventional) are excluded.
NON_SHARIAH = {
    # Conventional banking
    "1155.KL",   # Maybank
    "1295.KL",   # Public Bank
    "1023.KL",   # CIMB Group
    "5819.KL",   # Hong Leong Bank
    "1066.KL",   # RHB Bank
    "1015.KL",   # AMMB Holdings
    "2488.KL",   # Alliance Bank
    "1082.KL",   # Hong Leong Financial
    "5185.KL",   # AFFIN Bank

    # Insurance (conventional)
    "1163.KL",   # Allianz Malaysia
    "8621.KL",   # LPI Capital
    "1058.KL",   # Manulife

    # Breweries & Liquor
    "3255.KL",   # Heineken Malaysia
    "2836.KL",   # Carlsberg Brewery

    # Gaming
    "3182.KL",   # Genting Bhd
    "4715.KL",   # Genting Malaysia
}


from typing import List, Tuple


def get_all_symbols(shariah_only: bool = False) -> List[str]:
    """Return list of all Bursa Malaysia ticker symbols."""
    if shariah_only:
        return [s for s in SYMBOLS if s not in NON_SHARIAH]
    return list(SYMBOLS.keys())


def get_symbol_name(symbol: str) -> str:
    """Return company name for a given symbol."""
    return SYMBOLS.get(symbol, symbol)


def is_shariah(symbol: str) -> bool:
    """Check if a stock is Shariah-compliant."""
    return symbol not in NON_SHARIAH


def search_symbol(query: str, shariah_only: bool = False) -> List[Tuple[str, str]]:
    """Search symbols by name or code."""
    query = query.upper()
    results = []
    for code, name in SYMBOLS.items():
        if shariah_only and code in NON_SHARIAH:
            continue
        if query in code or query in name.upper():
            results.append((code, name))
    return results
