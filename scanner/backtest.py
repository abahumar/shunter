"""
Backtester for Stock Hunter scanner.

Simulates the real workflow:
1. At each market close, run the scanner on historical data up to that day
2. Buy top N BUY-signal stocks at next day's market open
3. Hold until a SELL signal triggers, then sell at next day's open
4. Track all trades and compute performance metrics
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock, classify_signal
from scanner.market_sentiment import compute_sentiment_at, KLCI_SYMBOL
from scanner.data_fetcher import fetch_stock_data

console = Console()


def _compute_indicators_at(df: pd.DataFrame, end_idx: int) -> Optional[dict]:
    """Compute indicators using data only up to end_idx (simulates point-in-time)."""
    if end_idx < 200:
        return None
    sliced = df.iloc[:end_idx + 1].copy()
    try:
        sliced = compute_indicators(sliced)
        return get_latest_indicators(sliced)
    except Exception:
        return None


def backtest(
    stock_data: Dict[str, pd.DataFrame],
    symbol_names: Dict[str, str],
    lookback_days: int = 60,
    top_n: int = 10,
    scan_interval: int = 5,
    stop_loss_pct: float = -7.0,
    min_price: float = 0.10,
    max_price: float = 0.0,
    trailing_stop: bool = False,
    signal_filter: str = "BUY",
    capital: float = 10000.0,
    volume_confirm: bool = True,
    trend_confirm: bool = True,
    take_profit_atr: float = 3.0,
    market_filter: bool = True,
    signal_confirmation: bool = True,
) -> dict:
    """
    Run backtest simulation with capital allocation (paper trade).

    Args:
        stock_data: dict of symbol -> full OHLCV DataFrame
        symbol_names: dict of symbol -> company name
        lookback_days: how many trading days to backtest
        top_n: max stocks to buy per scan day
        scan_interval: scan every N trading days (to simulate weekly scans)
        stop_loss_pct: stop-loss percentage (e.g., -7.0 means sell if down 7%)
        min_price: minimum stock price to consider (default: 0.10)
        max_price: maximum stock price to consider (0 = no limit)
        signal_filter: "BUY" (BUY+STRONG BUY) or "STRONG_BUY" (STRONG BUY only)
        capital: starting capital in RM (default: 10000)
        volume_confirm: require volume > 1.5x average to buy (default: True)
        trend_confirm: require ADX > 25 and DI+ > DI- to buy (default: True)
        take_profit_atr: sell when price reaches entry + N*ATR (0 = disabled)
        market_filter: apply KLCI sentiment score adjustment (default: True)
        signal_confirmation: require BUY in consecutive scans to buy (default: True)

    Returns:
        dict with trades, metrics, equity curve, and summary
    """
    # Use a reference stock to get trading dates
    ref_symbol = max(stock_data, key=lambda s: len(stock_data[s]))
    ref_df = stock_data[ref_symbol]
    total_bars = len(ref_df)

    if total_bars < lookback_days + 200:
        lookback_days = max(20, total_bars - 200)

    start_idx = total_bars - lookback_days
    end_idx = total_bars - 1
    trading_dates = ref_df.index[start_idx:end_idx + 1]

    trades: List[dict] = []          # completed trades
    open_positions: Dict[str, dict] = {}  # symbol -> position info
    scan_count = 0
    prev_buy_symbols: set = set()    # for consecutive signal confirmation

    # Fetch KLCI data for market sentiment filter
    klci_df = None
    if market_filter:
        try:
            klci_df = fetch_stock_data(KLCI_SYMBOL, period="1y")
        except Exception:
            pass

    # Paper trade state
    LOT_SIZE = 100  # Bursa Malaysia lot size
    cash = capital
    equity_curve = []  # list of {date, cash, invested, total}

    console.print(f"[dim]Backtesting {lookback_days} trading days, scanning every {scan_interval} days...[/dim]\n")

    for day_offset in range(lookback_days - 1):
        current_idx = start_idx + day_offset
        current_date = ref_df.index[current_idx]
        next_idx = current_idx + 1

        if next_idx >= total_bars:
            break

        next_date = ref_df.index[next_idx]

        # ── Check STOP-LOSS and SELL signals on open positions ──
        symbols_to_close = []
        for symbol, pos in open_positions.items():
            if symbol not in stock_data:
                continue
            sdf = stock_data[symbol]
            sym_idx = sdf.index.get_indexer([current_date], method="nearest")[0]
            if sym_idx < 200 or sym_idx >= len(sdf) - 1:
                continue

            current_close = sdf.iloc[sym_idx]["Close"]

            # Trailing stop: update highest price seen
            if trailing_stop:
                if "highest" not in pos:
                    pos["highest"] = pos["buy_price"]
                pos["highest"] = max(pos["highest"], current_close)
                stop_ref = pos["highest"]
            else:
                stop_ref = pos["buy_price"]

            current_pnl_from_stop = ((current_close - stop_ref) / stop_ref) * 100

            # Stop-loss: sell if price drops below threshold from reference
            if stop_loss_pct is not None and current_pnl_from_stop <= stop_loss_pct:
                sym_next_idx = sym_idx + 1
                if sym_next_idx < len(sdf):
                    sell_price = sdf.iloc[sym_next_idx]["Open"]
                    sell_date = sdf.index[sym_next_idx]
                    pnl_pct = ((sell_price - pos["buy_price"]) / pos["buy_price"]) * 100
                    hold_days = (sell_date - pos["buy_date"]).days
                    qty = pos.get("quantity", 0)
                    cost = pos["buy_price"] * qty
                    proceeds = sell_price * qty
                    pnl_rm = proceeds - cost
                    cash += proceeds

                    trades.append({
                        "symbol": symbol,
                        "name": symbol_names.get(symbol, symbol),
                        "buy_date": pos["buy_date"],
                        "buy_price": pos["buy_price"],
                        "buy_score": pos["buy_score"],
                        "sell_date": sell_date,
                        "sell_price": sell_price,
                        "sell_signal": "TRAILING-STOP" if trailing_stop else "STOP-LOSS",
                        "pnl_pct": pnl_pct,
                        "pnl_rm": round(pnl_rm, 2),
                        "quantity": qty,
                        "cost": round(cost, 2),
                        "hold_days": hold_days,
                    })
                    symbols_to_close.append(symbol)
                continue

            # Take-profit: sell when price reaches entry + N*ATR
            if take_profit_atr > 0 and "entry_atr" in pos:
                tp_target = pos["buy_price"] + (take_profit_atr * pos["entry_atr"])
                if current_close >= tp_target:
                    sym_next_idx = sym_idx + 1
                    if sym_next_idx < len(sdf):
                        sell_price = sdf.iloc[sym_next_idx]["Open"]
                        sell_date = sdf.index[sym_next_idx]
                        pnl_pct = ((sell_price - pos["buy_price"]) / pos["buy_price"]) * 100
                        hold_days = (sell_date - pos["buy_date"]).days
                        qty = pos.get("quantity", 0)
                        cost = pos["buy_price"] * qty
                        proceeds = sell_price * qty
                        pnl_rm = proceeds - cost
                        cash += proceeds

                        trades.append({
                            "symbol": symbol,
                            "name": symbol_names.get(symbol, symbol),
                            "buy_date": pos["buy_date"],
                            "buy_price": pos["buy_price"],
                            "buy_score": pos["buy_score"],
                            "sell_date": sell_date,
                            "sell_price": sell_price,
                            "sell_signal": "TAKE-PROFIT",
                            "pnl_pct": pnl_pct,
                            "pnl_rm": round(pnl_rm, 2),
                            "quantity": qty,
                            "cost": round(cost, 2),
                            "hold_days": hold_days,
                        })
                        symbols_to_close.append(symbol)
                    continue

            # Normal SELL signal check
            ind = _compute_indicators_at(sdf, sym_idx)
            if ind is None:
                continue

            analysis = analyze_stock(ind)
            if analysis["signal"] in ("SELL", "STRONG SELL"):
                # Sell at next day's open
                sym_next_idx = sym_idx + 1
                if sym_next_idx < len(sdf):
                    sell_price = sdf.iloc[sym_next_idx]["Open"]
                    sell_date = sdf.index[sym_next_idx]
                    pnl_pct = ((sell_price - pos["buy_price"]) / pos["buy_price"]) * 100
                    hold_days = (sell_date - pos["buy_date"]).days
                    qty = pos.get("quantity", 0)
                    cost = pos["buy_price"] * qty
                    proceeds = sell_price * qty
                    pnl_rm = proceeds - cost
                    cash += proceeds

                    trades.append({
                        "symbol": symbol,
                        "name": symbol_names.get(symbol, symbol),
                        "buy_date": pos["buy_date"],
                        "buy_price": pos["buy_price"],
                        "buy_score": pos["buy_score"],
                        "sell_date": sell_date,
                        "sell_price": sell_price,
                        "sell_signal": analysis["signal"],
                        "pnl_pct": pnl_pct,
                        "pnl_rm": round(pnl_rm, 2),
                        "quantity": qty,
                        "cost": round(cost, 2),
                        "hold_days": hold_days,
                    })
                    symbols_to_close.append(symbol)

        for s in symbols_to_close:
            del open_positions[s]

        # ── Scan for BUY signals every N days ──
        if day_offset % scan_interval != 0:
            continue
        scan_count += 1

        candidates = []
        for symbol, sdf in stock_data.items():
            if symbol in open_positions:
                continue

            sym_idx = sdf.index.get_indexer([current_date], method="nearest")[0]
            if sym_idx < 200 or sym_idx >= len(sdf) - 1:
                continue

            # Make sure the nearest date is actually close
            matched_date = sdf.index[sym_idx]
            if abs((matched_date - current_date).days) > 3:
                continue

            ind = _compute_indicators_at(sdf, sym_idx)
            if ind is None:
                continue

            analysis = analyze_stock(ind)
            allowed = ("STRONG BUY",) if signal_filter == "STRONG_BUY" else ("STRONG BUY", "BUY")
            if analysis["signal"] in allowed:
                # Volume confirmation: require volume > 1.5x average
                if volume_confirm:
                    vol = ind.get("volume", 0)
                    vol_avg = ind.get("volume_sma_20", 0)
                    if vol_avg and vol_avg > 0 and vol < 1.5 * vol_avg:
                        continue

                # Trend confirmation: require ADX > 25 and bullish direction
                if trend_confirm:
                    adx = ind.get("adx", 0) or 0
                    di_plus = ind.get("di_plus", 0) or 0
                    di_minus = ind.get("di_minus", 0) or 0
                    if adx < 25 or di_plus <= di_minus:
                        continue

                # Store ATR for take-profit calculation
                entry_atr = ind.get("atr", 0) or 0

                # Buy at next day's open
                sym_next_idx = sym_idx + 1
                if sym_next_idx < len(sdf):
                    buy_price = sdf.iloc[sym_next_idx]["Open"]
                    # Price range filter
                    if buy_price < min_price:
                        continue
                    if max_price > 0 and buy_price > max_price:
                        continue
                    buy_date = sdf.index[sym_next_idx]
                    candidates.append({
                        "symbol": symbol,
                        "buy_price": buy_price,
                        "buy_date": buy_date,
                        "net_score": analysis["net_score"],
                        "signal": analysis["signal"],
                        "entry_atr": entry_atr,
                    })

        # Pick top N by score — allocate capital per position
        # Apply market sentiment adjustment
        if market_filter and klci_df is not None:
            klci_idx = klci_df.index.get_indexer([current_date], method="nearest")[0]
            sentiment = compute_sentiment_at(klci_df, klci_idx)
            for c in candidates:
                c["net_score"] += sentiment.get("score_adj", 0)

        # Signal confirmation: prefer stocks that were BUY in previous scan too
        current_buy_symbols = {c["symbol"] for c in candidates}
        if signal_confirmation and scan_count > 1:
            for c in candidates:
                if c["symbol"] in prev_buy_symbols:
                    c["net_score"] += 10  # Confirmed signal bonus
        prev_buy_symbols = current_buy_symbols

        candidates.sort(key=lambda x: x["net_score"], reverse=True)
        slots_available = max(0, top_n - len(open_positions))
        per_position = cash / slots_available if slots_available > 0 else 0

        for c in candidates[:slots_available]:
            if c["symbol"] not in open_positions and per_position > 0:
                lots = int(per_position / (c["buy_price"] * LOT_SIZE))
                if lots < 1:
                    continue
                qty = lots * LOT_SIZE
                cost = c["buy_price"] * qty
                if cost > cash:
                    continue
                cash -= cost
                open_positions[c["symbol"]] = {
                    "buy_price": c["buy_price"],
                    "buy_date": c["buy_date"],
                    "buy_score": c["net_score"],
                    "quantity": qty,
                    "cost": cost,
                    "entry_atr": c.get("entry_atr", 0),
                }

        # Record equity curve point
        invested = sum(pos.get("cost", 0) for pos in open_positions.values())
        # Estimate current value of open positions
        unrealised = 0
        for sym, pos in open_positions.items():
            if sym in stock_data:
                sdf = stock_data[sym]
                si = sdf.index.get_indexer([current_date], method="nearest")[0]
                if 0 <= si < len(sdf):
                    unrealised += sdf.iloc[si]["Close"] * pos.get("quantity", 0)
        equity_curve.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "cash": round(cash, 2),
            "invested": round(invested, 2),
            "total": round(cash + unrealised, 2),
        })

    # ── Close remaining open positions at last available price ──
    last_date = ref_df.index[end_idx]
    for symbol, pos in open_positions.items():
        if symbol not in stock_data:
            continue
        sdf = stock_data[symbol]
        if len(sdf) == 0:
            continue
        last_price = sdf.iloc[-1]["Close"]
        pnl_pct = ((last_price - pos["buy_price"]) / pos["buy_price"]) * 100
        hold_days = (sdf.index[-1] - pos["buy_date"]).days
        qty = pos.get("quantity", 0)
        cost = pos["buy_price"] * qty
        proceeds = last_price * qty
        pnl_rm = proceeds - cost

        trades.append({
            "symbol": symbol,
            "name": symbol_names.get(symbol, symbol),
            "buy_date": pos["buy_date"],
            "buy_price": pos["buy_price"],
            "buy_score": pos["buy_score"],
            "sell_date": sdf.index[-1],
            "sell_price": last_price,
            "sell_signal": "STILL OPEN",
            "pnl_pct": pnl_pct,
            "pnl_rm": round(pnl_rm, 2),
            "quantity": qty,
            "cost": round(cost, 2),
            "hold_days": hold_days,
        })

    # ── Compute metrics ──
    metrics = _compute_metrics(trades)
    metrics["scan_count"] = scan_count
    metrics["backtest_days"] = lookback_days
    metrics["stop_loss_pct"] = stop_loss_pct
    metrics["min_price"] = min_price
    metrics["max_price"] = max_price

    # Capital metrics
    total_pnl_rm = sum(t.get("pnl_rm", 0) for t in trades)
    ending_capital = capital + total_pnl_rm
    metrics["starting_capital"] = capital
    metrics["ending_capital"] = round(ending_capital, 2)
    metrics["total_pnl_rm"] = round(total_pnl_rm, 2)
    metrics["capital_return_pct"] = round((total_pnl_rm / capital) * 100, 2) if capital > 0 else 0

    return {"trades": trades, "metrics": metrics, "equity_curve": equity_curve}


def _compute_metrics(trades: List[dict]) -> dict:
    """Compute backtest performance metrics."""
    if not trades:
        return {
            "total_trades": 0, "winners": 0, "losers": 0, "win_rate": 0,
            "avg_pnl": 0, "avg_winner": 0, "avg_loser": 0,
            "best_trade": 0, "worst_trade": 0, "total_return": 0,
            "avg_hold_days": 0, "profit_factor": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p <= 0]
    hold_days = [t["hold_days"] for t in trades]

    gross_profit = sum(winners) if winners else 0
    gross_loss = abs(sum(losers)) if losers else 0

    stop_losses = [t for t in trades if t.get("sell_signal") == "STOP-LOSS"]
    take_profits = [t for t in trades if t.get("sell_signal") == "TAKE-PROFIT"]

    return {
        "total_trades": len(trades),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": len(winners) / len(trades) * 100 if trades else 0,
        "avg_pnl": np.mean(pnls),
        "avg_winner": np.mean(winners) if winners else 0,
        "avg_loser": np.mean(losers) if losers else 0,
        "best_trade": max(pnls),
        "worst_trade": min(pnls),
        "total_return": sum(pnls),
        "avg_hold_days": np.mean(hold_days),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "stop_loss_exits": len(stop_losses),
        "take_profit_exits": len(take_profits),
    }


def print_backtest_results(result: dict):
    """Display backtest results in rich formatted tables."""
    trades = result["trades"]
    m = result["metrics"]

    if not trades:
        console.print("[yellow]No trades were generated during the backtest period.[/yellow]")
        return

    # ── Summary Panel ──
    win_style = "green" if m["win_rate"] >= 50 else "red"
    pnl_style = "green" if m["total_return"] > 0 else "red"

    stop_loss_line = ""
    if m.get("stop_loss_pct") is not None:
        stop_loss_line = (
            f"\n[bold]Stop-Loss:[/bold] {m['stop_loss_pct']:.0f}%  |  "
            f"Triggered: [red]{m.get('stop_loss_exits', 0)} times[/red]"
        )

    price_line = ""
    min_p = m.get("min_price", 0)
    max_p = m.get("max_price", 0)
    if min_p > 0 or max_p > 0:
        max_str = f"RM {max_p:.2f}" if max_p > 0 else "No limit"
        price_line = f"\n[bold]Price Filter:[/bold] RM {min_p:.2f} – {max_str}"

    summary = (
        f"[bold]Backtest Period:[/bold] {m['backtest_days']} trading days  |  "
        f"Scans: {m['scan_count']}\n"
        f"[bold]Total Trades:[/bold] {m['total_trades']}  |  "
        f"[green]Winners: {m['winners']}[/green]  |  "
        f"[red]Losers: {m['losers']}[/red]  |  "
        f"Win Rate: [{win_style}]{m['win_rate']:.1f}%[/{win_style}]\n"
        f"[bold]Avg P/L:[/bold] [{pnl_style}]{m['avg_pnl']:+.2f}%[/{pnl_style}]  |  "
        f"Avg Winner: [green]+{m['avg_winner']:.2f}%[/green]  |  "
        f"Avg Loser: [red]{m['avg_loser']:.2f}%[/red]\n"
        f"[bold]Best Trade:[/bold] [green]+{m['best_trade']:.2f}%[/green]  |  "
        f"Worst Trade: [red]{m['worst_trade']:.2f}%[/red]  |  "
        f"Profit Factor: {m['profit_factor']:.2f}\n"
        f"[bold]Total Return (sum):[/bold] [{pnl_style}]{m['total_return']:+.2f}%[/{pnl_style}]  |  "
        f"Avg Hold: {m['avg_hold_days']:.0f} days"
        f"{stop_loss_line}"
        f"{price_line}"
    )
    console.print(Panel(summary, title="📊 Backtest Results", border_style="cyan", box=box.ROUNDED))

    # ── Trades Table ──
    trades_sorted = sorted(trades, key=lambda t: t["pnl_pct"], reverse=True)

    table = Table(
        title="📋 All Trades (sorted by P/L)",
        box=box.SIMPLE_HEAVY,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Symbol", style="cyan", width=10)
    table.add_column("Name", width=20)
    table.add_column("Buy Date", width=12)
    table.add_column("Buy Price", justify="right", width=10)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Sell Date", width=12)
    table.add_column("Sell Price", justify="right", width=10)
    table.add_column("Exit", width=12)
    table.add_column("P/L %", justify="right", width=8)
    table.add_column("Days", justify="right", width=5)

    for i, t in enumerate(trades_sorted, 1):
        pnl = t["pnl_pct"]
        pnl_style = "green" if pnl > 0 else "red"
        exit_style = "dim" if t["sell_signal"] == "STILL OPEN" else ("bold red" if t["sell_signal"] == "STOP-LOSS" else ("red" if "SELL" in t["sell_signal"] else ""))

        table.add_row(
            str(i),
            t["symbol"],
            t.get("name", "")[:20],
            str(t["buy_date"])[:10],
            f"{t['buy_price']:.2f}",
            str(t.get("buy_score", "")),
            str(t["sell_date"])[:10],
            f"{t['sell_price']:.2f}",
            Text(t["sell_signal"], style=exit_style),
            Text(f"{pnl:+.2f}%", style=pnl_style),
            str(t["hold_days"]),
        )

    console.print(table)

    # ── Win/Loss distribution ──
    console.print()
    big_winners = [t for t in trades if t["pnl_pct"] > 5]
    big_losers = [t for t in trades if t["pnl_pct"] < -5]
    still_open = [t for t in trades if t["sell_signal"] == "STILL OPEN"]

    if big_winners:
        console.print(f"[green]🏆 Big winners (>5%): {len(big_winners)} trades[/green]")
    if big_losers:
        console.print(f"[red]💀 Big losers (<-5%): {len(big_losers)} trades[/red]")
    if still_open:
        console.print(f"[yellow]📌 Still open positions: {len(still_open)}[/yellow]")
    console.print()
