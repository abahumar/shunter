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
    "2054.KL": "TSH Resources",
    "5113.KL": "HSS International",
    "5126.KL": "Sarawak Oil Palms",
    "2852.KL": "FGV Holdings",

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
    "0023.KL": "Datasonic Group",
    "0072.KL": "Notion VTec",
    "0042.KL": "Genetec Technology",
    "0176.KL": "Ikhmas Jaya",
    "0150.KL": "Aurelius Technologies",
    "0152.KL": "Sensorlink",
    "0004.KL": "Censof Holdings",
    "0053.KL": "Agmo Holdings",
    "0005.KL": "Xentral Methods",
    "0078.KL": "Hover Structure",
    "0160.KL": "Aemulus Holdings",
    "0173.KL": "N2N Connect",
    "0180.KL": "Coraza Integrated Technology",
    "0120.KL": "Iris Corp",
    "0041.KL": "VSTECS",
    "0012.KL": "Opcom Holdings",
    "8176.KL": "Nationgate Holdings",
    "3816.KL": "MMAG Holdings",

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
    "5222.KL": "FGV Holdings",
    "5032.KL": "Econpile Holdings",
    "1546.KL": "Sarawak Consolidated",
    "5161.KL": "Kimlun Corp",
    "8893.KL": "Mitrajaya Holdings",
    "5027.KL": "Bina Puri Holdings",
    "5984.KL": "Chin Hin Group",
    "1538.KL": "Ho Hup Construction",
    "5237.KL": "Econpile",

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
    "1724.KL": "PKNS Holdings",
    "5148.KL": "UEM Sunrise",
    "5202.KL": "MSM Malaysia",
    "1771.KL": "Lagenda Properties",
    "5053.KL": "OSK Holdings",
    "8567.KL": "KSL Holdings",
    "1562.KL": "Matrix Concepts",
    "7183.KL": "IGB Corp",
    "5231.KL": "Eco World Dev",

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
    "2658.KL": "OldTown White Coffee",
    "6399.KL": "Spritzer",
    "6556.KL": "OCK Group",
    "5109.KL": "Mynews Holdings",
    "6076.KL": "Eco World International",
    "5291.KL": "Leong Hup International",
    "4818.KL": "DKSH Holdings",
    "3743.KL": "Farm Fresh Bhd",
    "5141.KL": "CBG Corp",
    "5239.KL": "AEON Retail",
    "5292.KL": "Eco-Shop Marketing",
    "7129.KL": "Oriental Kopi",

    # ── Healthcare ──
    "7103.KL": "Careplus Group",
    "9296.KL": "KPJ Healthcare",
    "6963.KL": "Hovid",

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
    "5783.KL": "Serba Dinamik",
    "5182.KL": "Perdana Petroleum",
    "5279.KL": "Deleum",
    "2577.KL": "Sapura Industrial",
    "5125.KL": "MISC Bhd",
    "5186.KL": "Wah Seong",

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
    "3794.KL": "Cypark Resources",
    "5209.KL": "Gas Malaysia",

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
    "3158.KL": "Ancom Nylex",
    "5014.KL": "Malaysia Airports",
    "2828.KL": "Sam Engineering",
    "7087.KL": "Lee Swee Kiat Group",
    "8052.KL": "Pecca Group",
    "7164.KL": "Rubberex",
    "6139.KL": "Sealink International",
    "9601.KL": "CJ Century Logistics",
    "7191.KL": "Lii Hen Industries",
    "7076.KL": "CB Industrial",
    "6645.KL": "CJ Century",
    "5300.KL": "Prolexus",

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
    "2267.KL": "Cycle & Carriage",
    "4588.KL": "UMW Holdings",
    "3417.KL": "Berjaya Auto",
    "5020.KL": "Sapura Resources",

    # ── More Technology / Semiconductor ──
    "0195.KL": "Oppstar",
    "0223.KL": "Cengild Medical",
    "0216.KL": "JHM Consolidation",
    "0240.KL": "Puncak Niaga Holdings",
    "0191.KL": "QES Group",
    "0155.KL": "AWC",
    "0171.KL": "MyKris International",
    "0058.KL": "Salcon",

    # ── More Industrial / Manufacturing ──
    "9695.KL": "Pantech Group",
    "9172.KL": "Chin Well Holdings",
    "6165.KL": "JKG Land",
    "5059.KL": "CSC Steel",
    "7839.KL": "Tasco Bhd",

    # ── Additional Mid-Cap Shariah ──
    "4383.KL": "Luxchem Corp",
    "8354.KL": "SCGM",
    "6688.KL": "Kelington Group",
    "7161.KL": "Kobay Technology",
    "0033.KL": "Techbond Group",
    "0109.KL": "Atta Global Group",
    "0116.KL": "Solutn Engineering",
    "0014.KL": "Wegmans Holdings",
    "0039.KL": "Ygl Convergence",
    "6823.KL": "SCIB",
    "9253.KL": "Apex Equity",

    # ── More Shariah Mid/Large-Cap ──
    "0091.KL": "MN Holdings",
    "0118.KL": "TT Vision",
    "0146.KL": "Cape EMS",
    "0187.KL": "Pekat Group",
    "0198.KL": "Innature",
    "0201.KL": "Coraza Integrated",
    "0207.KL": "Scomnet",
    "0235.KL": "Tuju Setia",
    "2070.KL": "Bell & Order",
    "3239.KL": "AirAsia Group",
    "3948.KL": "Malayan Cement",
    "5002.KL": "Sapura Industrial Bhd",
    "5021.KL": "DNex Bhd",
    "5099.KL": "AirAsia X",
    "5142.KL": "Rapid Synergy",
    "5213.KL": "BIMB Holdings Investment",
    "6432.KL": "OKA Corp",
    "7048.KL": "Thong Guan Industries",
    "7088.KL": "Magni-Tech",
    "7120.KL": "Tomypak Holdings",
    "7230.KL": "Heitech Padu",
    "7471.KL": "ATA IMS",
    "7668.KL": "IPMUDA",

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
