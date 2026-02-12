"""
Bursa Malaysia stock symbols list.
Tickers use the .KL suffix on Yahoo Finance (e.g., 1155.KL = Maybank).
"""

# Top ~200 actively traded Bursa Malaysia stocks across Main Market & ACE Market.
# Grouped by sector for reference. All use Yahoo Finance .KL suffix.

SYMBOLS = {
    # ── Banking & Finance ──
    "1155.KL": "Maybank",
    "1295.KL": "Public Bank",
    "6888.KL": "CIMB Group",
    "5819.KL": "Hong Leong Bank",
    "1066.KL": "RHB Bank",
    "5185.KL": "AMMB Holdings",
    "8583.KL": "Alliance Bank",
    "5053.KL": "Hong Leong Financial",
    "1023.KL": "BIMB Holdings",
    "5258.KL": "MBSB",
    "6947.KL": "Bursa Malaysia",
    "5291.KL": "Allianz Malaysia",
    "1818.KL": "LPI Capital",
    "6012.KL": "Manulife",
    "1015.KL": "AEON Credit",

    # ── Plantation ──
    "4863.KL": "Telekom Malaysia",
    "5285.KL": "Sime Darby Plantation",
    "2445.KL": "KLK",
    "1961.KL": "IOI Corp",
    "5211.KL": "Sime Darby",
    "2291.KL": "Genting Plantations",
    "2054.KL": "FGV Holdings",
    "5113.KL": "Hap Seng Plantations",
    "5126.KL": "Ta Ann Holdings",
    "2852.KL": "IJM Plantations",

    # ── Technology ──
    "0166.KL": "Inari Amertron",
    "0023.KL": "Datasonic",
    "5264.KL": "Vitrox",
    "0042.KL": "Frontken",
    "0072.KL": "Unisem",
    "0180.KL": "D&O Green Tech",
    "5318.KL": "Globetronics",
    "0041.KL": "MI Technovation",
    "0078.KL": "Elsoft Research",
    "0053.KL": "Pentamaster",
    "0005.KL": "Greatech Technology",
    "0160.KL": "Uchi Technologies",
    "0173.KL": "KESM Industries",
    "0200.KL": "MyEG Services",
    "5765.KL": "UEM Edgenta",

    # ── Construction & Infrastructure ──
    "5398.KL": "Gamuda",
    "3336.KL": "IJM Corp",
    "5222.KL": "WCT Holdings",
    "8206.KL": "MRCB",
    "5032.KL": "Sunway Construction",
    "1546.KL": "Ekovest",
    "5161.KL": "Muhibbah Engineering",
    "8893.KL": "HSS Engineers",
    "5027.KL": "George Kent",

    # ── Property & REIT ──
    "1724.KL": "SP Setia",
    "5148.KL": "IOI Properties",
    "8664.KL": "Eco World Development",
    "5168.KL": "UOA Development",
    "1651.KL": "Mah Sing Group",
    "5202.KL": "Sunway Bhd",
    "1771.KL": "IGB REIT",
    "5227.KL": "Pavilion REIT",
    "5106.KL": "Axis REIT",
    "5183.KL": "Sunway REIT",
    "5212.KL": "KLCCP Stapled",
    "5180.KL": "Sentral REIT",
    "5235.KL": "CapitaLand Malaysia Mall Trust",

    # ── Consumer & Retail ──
    "4715.KL": "Nestle Malaysia",
    "3689.KL": "Fraser & Neave",
    "4707.KL": "Dutch Lady",
    "2658.KL": "Heineken Malaysia",
    "3255.KL": "Carlsberg Brewery",
    "5225.KL": "IHH Healthcare",
    "6399.KL": "QL Resources",
    "7113.KL": "Top Glove",
    "7153.KL": "Kossan Rubber",
    "7084.KL": "Hartalega",
    "5347.KL": "Supermax",
    "7103.KL": "Comfort Gloves",
    "5296.KL": "Padini Holdings",
    "6556.KL": "Aeon Co",
    "5109.KL": "Mr DIY Group",

    # ── Oil & Gas / Energy ──
    "5681.KL": "Petronas Chemicals",
    "6033.KL": "Petronas Gas",
    "5783.KL": "Petronas Dagangan",
    "5218.KL": "Sapura Energy",
    "5182.KL": "Dialog Group",
    "5279.KL": "Serba Dinamik",
    "5243.KL": "Yinson Holdings",
    "2577.KL": "Uzma Bhd",
    "5125.KL": "Bumi Armada",
    "7052.KL": "Hibiscus Petroleum",
    "5186.KL": "Velesto Energy",

    # ── Telecommunications ──
    "6947.KL": "Bursa Malaysia",
    "6012.KL": "Maxis",
    "6742.KL": "YTL Power",
    "6888.KL": "CIMB",
    "4818.KL": "Digi.Com",
    "3867.KL": "CelcomDigi",
    "0138.KL": "MyNews Holdings",

    # ── Utilities ──
    "5347.KL": "Tenaga Nasional",
    "6742.KL": "YTL Power",
    "5264.KL": "YTL Corp",
    "8524.KL": "Taliworks",
    "3794.KL": "Ranhill Utilities",

    # ── Industrial / Manufacturing ──
    "3158.KL": "Press Metal",
    "5014.KL": "Malaysia Airports",
    "4065.KL": "PPB Group",
    "5681.KL": "Petronas Chemicals",
    "2828.KL": "Westports Holdings",
    "3417.KL": "EP Manufacturing",
    "4197.KL": "SKP Resources",
    "8052.KL": "Poh Huat Resources",
    "7087.KL": "Scientex",
    "9296.KL": "Duopharma Biotech",
    "7106.KL": "Karex Bhd",
    "5200.KL": "UMS Holdings",
    "5014.KL": "MAHB",

    # ── Diversified / Others ──
    "4715.KL": "Genting Bhd",
    "3182.KL": "Genting Malaysia",
    "2267.KL": "Berjaya Corp",
    "1562.KL": "Berjaya Food",
    "6076.KL": "Hup Seng Industries",
    "7277.KL": "Dialog",
    "2488.KL": "Power Root",
    "6963.KL": "Apex Healthcare",
    "7090.KL": "Pharmaniaga",
    "2577.KL": "Kawan Food",
    "8567.KL": "Oceancash Pacific",

    # ── ACE Market (High Growth) ──
    "0166.KL": "Inari Amertron",
    "0023.KL": "Datasonic",
    "0004.KL": "Revenue Group",
    "0185.KL": "Pengerang LNG",
    "0176.KL": "Cuscapi",
    "0120.KL": "Ideal United Bintang",
    "0012.KL": "Opcom Holdings",
    "0097.KL": "Green Packet",
    "0150.KL": "Dagang NeXchange",
    "0152.KL": "Netx Holdings",
}


# ── Non-Shariah compliant stocks ──
# Based on Securities Commission Malaysia Shariah Advisory Council rulings.
# Conventional banks, breweries, gaming, liquor, and insurance (conventional) are excluded.
NON_SHARIAH = {
    # Conventional banking
    "1155.KL",   # Maybank (mixed, but conventional dominant)
    "1295.KL",   # Public Bank
    "6888.KL",   # CIMB Group
    "5819.KL",   # Hong Leong Bank
    "1066.KL",   # RHB Bank
    "5185.KL",   # AMMB Holdings
    "8583.KL",   # Alliance Bank
    "5053.KL",   # Hong Leong Financial

    # Insurance (conventional)
    "5291.KL",   # Allianz Malaysia
    "1818.KL",   # LPI Capital
    "6012.KL",   # Manulife

    # Breweries & Liquor
    "2658.KL",   # Heineken Malaysia
    "3255.KL",   # Carlsberg Brewery

    # Gaming
    "4715.KL",   # Genting Bhd
    "3182.KL",   # Genting Malaysia
    "6947.KL",   # Bursa Malaysia (deemed non-compliant by some lists)
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
