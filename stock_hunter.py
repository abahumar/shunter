#!/usr/bin/env python3
"""
Stock Hunter 🎯 - Malaysia Stock Filter
Scans Bursa Malaysia stocks and recommends BUY/SELL signals
for medium to long-term traders.

Usage:
    python stock_hunter.py scan              # Scan all stocks for BUY signals
    python stock_hunter.py scan --top 20     # Show top 20 results
    python stock_hunter.py check SYMBOL      # Check a specific stock
    python stock_hunter.py backtest          # Backtest the scanner (2-3 months)
    python stock_hunter.py portfolio         # Check sell signals on your portfolio
    python stock_hunter.py add SYMBOL PRICE  # Add stock to portfolio
    python stock_hunter.py remove SYMBOL     # Remove stock from portfolio
    python stock_hunter.py list              # List portfolio stocks
    python stock_hunter.py search QUERY      # Search for a stock by name/code
"""

import sys
import argparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from scanner.symbols import get_all_symbols, get_symbol_name, search_symbol, is_shariah
from scanner.data_fetcher import fetch_stock_data, fetch_bulk_data
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock
from scanner.backtest import backtest, print_backtest_results
from scanner.portfolio import add_stock, remove_stock, get_portfolio

console = Console()


SIGNAL_STYLES = {
    "STRONG BUY": "bold white on green",
    "BUY": "bold green",
    "WATCH": "bold yellow",
    "HOLD": "dim",
    "SELL": "bold red",
    "STRONG SELL": "bold white on red",
}


def print_banner():
    banner = Text()
    banner.append("🎯 Stock Hunter", style="bold cyan")
    banner.append(" - Bursa Malaysia Scanner\n", style="dim")
    banner.append("   Medium & Long-Term Trading Signals", style="italic")
    console.print(Panel(banner, box=box.ROUNDED, border_style="cyan"))


def format_signal(signal: str) -> Text:
    style = SIGNAL_STYLES.get(signal, "")
    return Text(f" {signal} ", style=style)


def cmd_scan(args):
    """Scan all Bursa Malaysia stocks for trading signals."""
    print_banner()
    top_n = args.top
    shariah = args.shariah
    label = "Shariah-compliant" if shariah else "all"
    console.print(f"\n[bold]Scanning {label} Bursa Malaysia stocks...[/bold]\n")

    symbols = get_all_symbols(shariah_only=shariah)
    data = fetch_bulk_data(symbols, period="1y", delay=0.2)

    console.print(f"\n[green]✓[/green] Analyzed [bold]{len(data)}[/bold] stocks\n")

    # Analyze each stock
    results = []
    for symbol, df in data.items():
        try:
            df = compute_indicators(df)
            ind = get_latest_indicators(df)
            analysis = analyze_stock(ind)
            analysis["symbol"] = symbol
            analysis["name"] = get_symbol_name(symbol)
            analysis["close"] = ind.get("close", 0)
            analysis["rsi"] = ind.get("rsi", 0)
            analysis["adx"] = ind.get("adx", 0)
            analysis["volume_ratio"] = (
                ind["volume"] / ind["volume_sma_20"]
                if ind.get("volume_sma_20") and ind["volume_sma_20"] > 0
                else 0
            )
            results.append(analysis)
        except Exception:
            continue

    # Sort by net score descending
    results.sort(key=lambda x: x["net_score"], reverse=True)

    # Show BUY signals
    buy_results = [r for r in results if r["signal"] in ("STRONG BUY", "BUY")]
    watch_results = [r for r in results if r["signal"] == "WATCH"]

    if buy_results:
        table = Table(
            title="🟢 BUY Signals",
            box=box.SIMPLE_HEAVY,
            show_lines=True,
        )
        table.add_column("Rank", style="dim", width=4)
        table.add_column("Symbol", style="cyan", width=10)
        table.add_column("Name", width=25)
        table.add_column("Price", justify="right", width=8)
        table.add_column("Signal", width=12)
        table.add_column("Score", justify="right", width=6)
        table.add_column("RSI", justify="right", width=5)
        table.add_column("ADX", justify="right", width=5)
        table.add_column("Vol", justify="right", width=6)
        table.add_column("Key Reasons", width=45)

        for i, r in enumerate(buy_results[:top_n], 1):
            top_reasons = "; ".join(r["buy_reasons"][:3])
            table.add_row(
                str(i),
                r["symbol"],
                r["name"][:25],
                f"{r['close']:.2f}",
                format_signal(r["signal"]),
                str(r["net_score"]),
                f"{r['rsi']:.0f}" if r["rsi"] else "-",
                f"{r['adx']:.0f}" if r["adx"] else "-",
                f"{r['volume_ratio']:.1f}x" if r["volume_ratio"] else "-",
                top_reasons,
            )
        console.print(table)
    else:
        console.print("[yellow]No strong BUY signals found at this time.[/yellow]")

    if watch_results:
        console.print(f"\n[yellow]👀 {len(watch_results)} stocks on WATCH list[/yellow]")
        watch_names = ", ".join(
            f"{r['symbol']} ({r['name'][:15]})" for r in watch_results[:10]
        )
        console.print(f"   {watch_names}")

    # Summary
    sell_count = len([r for r in results if r["signal"] in ("SELL", "STRONG SELL")])
    console.print(
        f"\n[dim]Summary: {len(buy_results)} BUY | {len(watch_results)} WATCH | {sell_count} SELL signals[/dim]\n"
    )


def cmd_check(args):
    """Check a specific stock in detail."""
    print_banner()
    symbol = args.symbol.upper()
    if not symbol.endswith(".KL"):
        symbol += ".KL"

    console.print(f"\n[bold]Analyzing {symbol}...[/bold]\n")

    df = fetch_stock_data(symbol, period="1y")
    if df is None:
        console.print(f"[red]✗ Could not fetch data for {symbol}[/red]")
        return

    df = compute_indicators(df)
    ind = get_latest_indicators(df)
    analysis = analyze_stock(ind)

    name = get_symbol_name(symbol)

    # Header
    signal = analysis["signal"]
    style = SIGNAL_STYLES.get(signal, "")
    console.print(Panel(
        f"[bold]{symbol}[/bold] - {name}\n"
        f"Price: [bold]RM {ind['close']:.2f}[/bold]   |   Signal: [{style}] {signal} [/{style}]   |   Score: {analysis['net_score']}",
        border_style="cyan",
    ))

    # Indicators table
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Indicator", style="dim", width=20)
    table.add_column("Value", width=15)
    table.add_column("Indicator", style="dim", width=20)
    table.add_column("Value", width=15)

    table.add_row(
        "EMA 20", f"{ind.get('ema_20', 0):.3f}" if ind.get('ema_20') else "-",
        "RSI (14)", f"{ind.get('rsi', 0):.1f}" if ind.get('rsi') else "-",
    )
    table.add_row(
        "EMA 50", f"{ind.get('ema_50', 0):.3f}" if ind.get('ema_50') else "-",
        "ADX", f"{ind.get('adx', 0):.1f}" if ind.get('adx') else "-",
    )
    table.add_row(
        "EMA 200", f"{ind.get('ema_200', 0):.3f}" if ind.get('ema_200') else "-",
        "MACD Hist", f"{ind.get('macd_hist', 0):.4f}" if ind.get('macd_hist') else "-",
    )
    table.add_row(
        "52w High", f"{ind.get('high_52w', 0):.3f}" if ind.get('high_52w') else "-",
        "Volume Ratio", f"{ind['volume'] / ind['volume_sma_20']:.1f}x" if ind.get('volume_sma_20') and ind['volume_sma_20'] > 0 else "-",
    )
    table.add_row(
        "52w Low", f"{ind.get('low_52w', 0):.3f}" if ind.get('low_52w') else "-",
        "ATR", f"{ind.get('atr', 0):.4f}" if ind.get('atr') else "-",
    )
    console.print(table)

    # Reasons
    if analysis["buy_reasons"]:
        console.print("\n[green]✓ Bullish signals:[/green]")
        for r in analysis["buy_reasons"]:
            console.print(f"  [green]•[/green] {r}")

    if analysis["sell_reasons"]:
        console.print("\n[red]✗ Bearish signals:[/red]")
        for r in analysis["sell_reasons"]:
            console.print(f"  [red]•[/red] {r}")

    console.print()


def cmd_backtest(args):
    """Backtest the scanner strategy on historical data."""
    print_banner()
    days = args.days
    top_n = args.top
    interval = args.interval
    stop_loss = args.stop_loss if args.stop_loss != 0 else None
    min_price = args.min_price
    max_price = args.max_price
    shariah = args.shariah

    sl_text = f", stop-loss {stop_loss}%" if stop_loss is not None else ""
    price_text = f", RM {min_price:.2f}-{max_price:.2f}" if max_price > 0 else f", min RM {min_price:.2f}"
    shariah_text = ", Shariah only ☪" if shariah else ""
    console.print(f"\n[bold]Running backtest: {days} trading days, top {top_n} picks, scan every {interval} days{sl_text}{price_text}{shariah_text}[/bold]\n")

    symbols = get_all_symbols(shariah_only=shariah)

    # Need extra history for indicator warm-up (200 EMA needs 200+ bars)
    period = "2y"
    data = fetch_bulk_data(symbols, period=period, delay=0.2)

    console.print(f"\n[green]✓[/green] Loaded data for [bold]{len(data)}[/bold] stocks\n")

    from scanner.symbols import SYMBOLS as symbol_names
    result = backtest(data, symbol_names, lookback_days=days, top_n=top_n, scan_interval=interval, stop_loss_pct=stop_loss, min_price=min_price, max_price=max_price)
    print_backtest_results(result)


def cmd_portfolio(args):
    """Check sell signals on portfolio stocks."""
    print_banner()
    stocks = get_portfolio()

    if not stocks:
        console.print("[yellow]Portfolio is empty. Use 'add' command to add stocks.[/yellow]")
        console.print("[dim]  python stock_hunter.py add 1155.KL 8.50[/dim]")
        return

    console.print(f"\n[bold]Checking {len(stocks)} portfolio stocks...[/bold]\n")

    table = Table(
        title="📊 Portfolio Status",
        box=box.SIMPLE_HEAVY,
        show_lines=True,
    )
    table.add_column("Symbol", style="cyan", width=10)
    table.add_column("Name", width=22)
    table.add_column("Buy Price", justify="right", width=10)
    table.add_column("Current", justify="right", width=10)
    table.add_column("P/L %", justify="right", width=8)
    table.add_column("Signal", width=12)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Action", width=35)

    for stock in stocks:
        symbol = stock["symbol"]
        buy_price = stock["buy_price"]

        df = fetch_stock_data(symbol, period="1y")
        if df is None:
            table.add_row(symbol, "-", f"{buy_price:.2f}", "-", "-", "-", "-", "No data")
            continue

        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        analysis = analyze_stock(ind)

        current = ind["close"]
        pnl = ((current - buy_price) / buy_price) * 100
        pnl_style = "green" if pnl >= 0 else "red"

        signal = analysis["signal"]
        action_parts = []
        if signal in ("SELL", "STRONG SELL"):
            action_parts = analysis["sell_reasons"][:2]
        elif signal in ("BUY", "STRONG BUY"):
            action_parts = ["Hold / Add position"]
        else:
            action_parts = ["Monitor"]

        table.add_row(
            symbol,
            get_symbol_name(symbol)[:22],
            f"{buy_price:.2f}",
            f"{current:.2f}",
            Text(f"{pnl:+.1f}%", style=pnl_style),
            format_signal(signal),
            str(analysis["net_score"]),
            "; ".join(action_parts)[:35],
        )

    console.print(table)

    # Sell alerts
    console.print()
    has_sell = False
    for stock in stocks:
        symbol = stock["symbol"]
        df = fetch_stock_data(symbol, period="6mo")
        if df is None:
            continue
        df = compute_indicators(df)
        ind = get_latest_indicators(df)
        analysis = analyze_stock(ind)
        if analysis["signal"] in ("SELL", "STRONG SELL"):
            if not has_sell:
                console.print("[bold red]⚠ SELL ALERTS:[/bold red]")
                has_sell = True
            console.print(
                f"  [red]🔴 {symbol}[/red] ({get_symbol_name(symbol)}) - "
                f"Consider selling: {'; '.join(analysis['sell_reasons'][:2])}"
            )

    if not has_sell:
        console.print("[green]✓ No sell alerts. All positions look okay.[/green]")
    console.print()


def cmd_add(args):
    """Add a stock to portfolio."""
    symbol = args.symbol.upper()
    if not symbol.endswith(".KL"):
        symbol += ".KL"

    price = args.price
    qty = args.quantity or 0
    add_stock(symbol, price, qty)
    console.print(f"[green]✓[/green] Added [bold]{symbol}[/bold] at RM {price:.2f} to portfolio")


def cmd_remove(args):
    """Remove a stock from portfolio."""
    symbol = args.symbol.upper()
    if not symbol.endswith(".KL"):
        symbol += ".KL"

    if remove_stock(symbol):
        console.print(f"[green]✓[/green] Removed [bold]{symbol}[/bold] from portfolio")
    else:
        console.print(f"[yellow]Stock {symbol} not found in portfolio[/yellow]")


def cmd_list(args):
    """List all portfolio stocks."""
    print_banner()
    stocks = get_portfolio()

    if not stocks:
        console.print("[yellow]Portfolio is empty.[/yellow]")
        return

    table = Table(title="📋 My Portfolio", box=box.SIMPLE)
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Buy Price", justify="right")
    table.add_column("Qty", justify="right")
    table.add_column("Added", style="dim")
    table.add_column("Notes")

    for s in stocks:
        table.add_row(
            s["symbol"],
            get_symbol_name(s["symbol"]),
            f"RM {s['buy_price']:.2f}",
            str(s.get("quantity", 0)),
            s.get("added_at", "")[:10],
            s.get("notes", ""),
        )
    console.print(table)


def cmd_search(args):
    """Search for a stock symbol."""
    results = search_symbol(args.query)
    if not results:
        console.print(f"[yellow]No stocks found for '{args.query}'[/yellow]")
        return

    table = Table(box=box.SIMPLE)
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    for code, name in results:
        table.add_row(code, name)
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="🎯 Stock Hunter - Bursa Malaysia Stock Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan all stocks for BUY signals")
    scan_parser.add_argument("--top", type=int, default=30, help="Show top N results (default: 30)")
    scan_parser.add_argument("--shariah", action="store_true", help="Shariah-compliant stocks only")
    scan_parser.set_defaults(func=cmd_scan)

    # check
    check_parser = subparsers.add_parser("check", help="Check a specific stock in detail")
    check_parser.add_argument("symbol", help="Stock symbol (e.g., 1155.KL or 1155)")
    check_parser.set_defaults(func=cmd_check)

    # backtest
    bt_parser = subparsers.add_parser("backtest", help="Backtest the scanner on historical data")
    bt_parser.add_argument("--days", type=int, default=60, help="Trading days to backtest (default: 60)")
    bt_parser.add_argument("--top", type=int, default=10, help="Max stocks to buy per scan (default: 10)")
    bt_parser.add_argument("--interval", type=int, default=5, help="Scan every N trading days (default: 5 = weekly)")
    bt_parser.add_argument("--stop-loss", type=float, default=-10.0, help="Stop-loss %% (default: -10.0, use 0 to disable)")
    bt_parser.add_argument("--min-price", type=float, default=0.50, help="Minimum stock price (default: 0.50)")
    bt_parser.add_argument("--max-price", type=float, default=0.0, help="Maximum stock price (default: 0 = no limit)")
    bt_parser.add_argument("--shariah", action="store_true", help="Shariah-compliant stocks only")
    bt_parser.set_defaults(func=cmd_backtest)

    # portfolio
    port_parser = subparsers.add_parser("portfolio", help="Check sell signals on your portfolio")
    port_parser.set_defaults(func=cmd_portfolio)

    # add
    add_parser = subparsers.add_parser("add", help="Add a stock to portfolio")
    add_parser.add_argument("symbol", help="Stock symbol")
    add_parser.add_argument("price", type=float, help="Buy price")
    add_parser.add_argument("--quantity", "-q", type=int, help="Number of shares")
    add_parser.set_defaults(func=cmd_add)

    # remove
    rm_parser = subparsers.add_parser("remove", help="Remove stock from portfolio")
    rm_parser.add_argument("symbol", help="Stock symbol")
    rm_parser.set_defaults(func=cmd_remove)

    # list
    list_parser = subparsers.add_parser("list", help="List portfolio stocks")
    list_parser.set_defaults(func=cmd_list)

    # search
    search_parser = subparsers.add_parser("search", help="Search for a stock")
    search_parser.add_argument("query", help="Search query (name or code)")
    search_parser.set_defaults(func=cmd_search)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        console.print("\n[dim]Quick start: python stock_hunter.py scan[/dim]")
        return

    args.func(args)


if __name__ == "__main__":
    main()
