"""
Technical indicator calculations for stock analysis.
Uses the `ta` library for reliable indicator computation.
"""

import pandas as pd
import ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to the OHLCV DataFrame.
    Returns the DataFrame with new indicator columns.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # ── Exponential Moving Averages ──
    df["EMA_20"] = ta.trend.ema_indicator(close, window=20)
    df["EMA_50"] = ta.trend.ema_indicator(close, window=50)
    df["EMA_200"] = ta.trend.ema_indicator(close, window=200)

    # ── MACD ──
    macd = ta.trend.MACD(close)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()

    # ── RSI ──
    df["RSI"] = ta.momentum.rsi(close, window=14)

    # ── Stochastic RSI ──
    stoch_rsi = ta.momentum.StochRSIIndicator(close, window=14)
    df["StochRSI_K"] = stoch_rsi.stochrsi_k()
    df["StochRSI_D"] = stoch_rsi.stochrsi_d()

    # ── ADX (Average Directional Index) ──
    adx = ta.trend.ADXIndicator(high, low, close, window=14)
    df["ADX"] = adx.adx()
    df["DI_plus"] = adx.adx_pos()
    df["DI_minus"] = adx.adx_neg()

    # ── Volume indicators ──
    df["Volume_SMA_20"] = volume.rolling(window=20).mean()
    df["OBV"] = ta.volume.on_balance_volume(close, volume)
    df["OBV_SMA_20"] = df["OBV"].rolling(window=20).mean()

    # ── 52-week High / Low ──
    df["High_52w"] = high.rolling(window=252, min_periods=50).max()
    df["Low_52w"] = low.rolling(window=252, min_periods=50).min()

    # ── Bollinger Bands ──
    bb = ta.volatility.BollingerBands(close, window=20)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    df["BB_mid"] = bb.bollinger_mavg()

    # ── ATR (Average True Range) for volatility ──
    df["ATR"] = ta.volatility.average_true_range(high, low, close, window=14)

    return df


def get_latest_indicators(df: pd.DataFrame) -> dict:
    """Extract the latest (most recent) indicator values as a dict."""
    if df.empty:
        return {}

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    return {
        "close": last["Close"],
        "open": last["Open"],
        "high": last["High"],
        "low": last["Low"],
        "volume": last["Volume"],

        "ema_20": last.get("EMA_20"),
        "ema_50": last.get("EMA_50"),
        "ema_200": last.get("EMA_200"),

        "macd": last.get("MACD"),
        "macd_signal": last.get("MACD_signal"),
        "macd_hist": last.get("MACD_hist"),
        "macd_hist_prev": prev.get("MACD_hist"),

        "rsi": last.get("RSI"),
        "stoch_rsi_k": last.get("StochRSI_K"),
        "stoch_rsi_d": last.get("StochRSI_D"),

        "adx": last.get("ADX"),
        "di_plus": last.get("DI_plus"),
        "di_minus": last.get("DI_minus"),

        "volume_sma_20": last.get("Volume_SMA_20"),
        "obv": last.get("OBV"),
        "obv_sma_20": last.get("OBV_SMA_20"),

        "high_52w": last.get("High_52w"),
        "low_52w": last.get("Low_52w"),

        "bb_upper": last.get("BB_upper"),
        "bb_lower": last.get("BB_lower"),
        "bb_mid": last.get("BB_mid"),

        "atr": last.get("ATR"),
    }
