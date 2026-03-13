#!/usr/bin/env python3
"""
polymarket-pnl — Instant P&L breakdown for any Polymarket wallet.

Usage:
    python3 pnl.py 0x1234...                  # Full P&L report
    python3 pnl.py 0x1234... --top 10         # Top 10 positions only
    python3 pnl.py 0x1234... --sport          # Sports positions only
    python3 pnl.py 0x1234... --losing         # Only losing positions
    python3 pnl.py 0x1234... --json           # Raw JSON output
    python3 pnl.py 0x1234... --csv            # CSV export
    python3 pnl.py leaderboard                # Top traders this week
    python3 pnl.py leaderboard --period=day   # Top traders today
"""

import argparse
import csv
import io
import json
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone


DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

# Sports-related keywords for categorization
SPORTS_KEYWORDS = [
    "nba", "nhl", "nfl", "mlb", "epl", "premier league", "la liga",
    "bundesliga", "serie a", "ligue 1", "champions league", "europa league",
    "mls", "ncaa", "super bowl", "world series", "stanley cup", "playoff",
    "win", "beat", "vs", "match", "game", "score",
    # Teams that only appear in sports
    "lakers", "celtics", "warriors", "cavaliers", "knicks", "nets",
    "lightning", "predators", "oilers", "maple leafs", "bruins",
    "yankees", "dodgers", "mets", "astros", "cubs",
    "chiefs", "eagles", "49ers", "cowboys", "packers",
    "arsenal", "liverpool", "chelsea", "manchester", "barcelona", "real madrid",
    "bayern", "juventus", "inter milan", "psg", "napoli",
]


def api_get(url, max_retries=2):
    """GET with retries and timeout."""
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "polymarket-pnl/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == max_retries:
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None
    return None


def fetch_positions(address):
    """Fetch all positions for a wallet address."""
    address = address.lower()  # Data API requires lowercase
    all_positions = []
    offset = 0
    limit = 100
    while True:
        url = f"{DATA_API}/positions?user={address}&limit={limit}&offset={offset}"
        data = api_get(url)
        if not data or len(data) == 0:
            break
        all_positions.extend(data)
        if len(data) < limit:
            break
        offset += limit
    return all_positions


def fetch_leaderboard(period="weekly", limit=20):
    """Fetch top traders from Polymarket leaderboard via Gamma API."""
    # Data API leaderboard is deprecated, use Gamma API
    url = f"{GAMMA_API}/leaderboard?window={period}&limit={limit}"
    data = api_get(url)
    if data:
        return data
    # Fallback: try data API activity endpoint for top traders by volume
    url = f"{DATA_API}/activity?limit={limit}&sortBy=volume&sortDirection=desc"
    data = api_get(url)
    return data if data else []


def is_sports(title):
    """Classify a market as sports-related."""
    t = title.lower()
    return any(kw in t for kw in SPORTS_KEYWORDS)


def safe_float(val, default=0.0):
    """Safely convert to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def analyze_positions(positions):
    """Compute full P&L breakdown from positions."""
    stats = {
        "total_positions": len(positions),
        "total_invested": 0,
        "total_current_value": 0,
        "total_cash_pnl": 0,
        "total_realized_pnl": 0,
        "winners": 0,
        "losers": 0,
        "open_positions": 0,
        "closed_positions": 0,
        "sports_positions": 0,
        "sports_pnl": 0,
        "political_positions": 0,
        "political_pnl": 0,
        "best_trade": None,
        "worst_trade": None,
        "positions": [],
    }

    for p in positions:
        cash_pnl = safe_float(p.get("cashPnl"))
        realized = safe_float(p.get("realizedPnl"))
        current_val = safe_float(p.get("currentValue"))
        initial_val = safe_float(p.get("initialValue"))
        size = safe_float(p.get("size"))
        avg_price = safe_float(p.get("avgPrice"))
        cur_price = safe_float(p.get("curPrice"))
        pct_pnl = safe_float(p.get("percentPnl"))

        title = p.get("title", "Unknown")
        outcome = p.get("outcome", "")
        slug = p.get("slug", "")
        asset = p.get("asset", "")

        pos_data = {
            "title": title,
            "outcome": outcome,
            "size": size,
            "avg_price": avg_price,
            "cur_price": cur_price,
            "initial_value": initial_val,
            "current_value": current_val,
            "cash_pnl": cash_pnl,
            "realized_pnl": realized,
            "percent_pnl": pct_pnl,
            "is_sports": is_sports(title),
            "is_open": current_val > 0.001,
        }

        stats["positions"].append(pos_data)
        stats["total_invested"] += initial_val
        stats["total_current_value"] += current_val
        stats["total_cash_pnl"] += cash_pnl
        stats["total_realized_pnl"] += realized

        if cash_pnl > 0:
            stats["winners"] += 1
        elif cash_pnl < 0:
            stats["losers"] += 1

        if pos_data["is_open"]:
            stats["open_positions"] += 1
        else:
            stats["closed_positions"] += 1

        if pos_data["is_sports"]:
            stats["sports_positions"] += 1
            stats["sports_pnl"] += cash_pnl
        else:
            stats["political_positions"] += 1
            stats["political_pnl"] += cash_pnl

        if stats["best_trade"] is None or cash_pnl > stats["best_trade"]["cash_pnl"]:
            stats["best_trade"] = pos_data
        if stats["worst_trade"] is None or cash_pnl < stats["worst_trade"]["cash_pnl"]:
            stats["worst_trade"] = pos_data

    win_rate = (stats["winners"] / stats["total_positions"] * 100) if stats["total_positions"] > 0 else 0
    stats["win_rate"] = win_rate
    stats["unrealized_pnl"] = stats["total_current_value"] - (stats["total_invested"] - abs(stats["total_realized_pnl"]))

    return stats


def format_money(val):
    """Format as dollar amount with color indicator."""
    if val >= 0:
        return f"+${val:,.2f}"
    return f"-${abs(val):,.2f}"


def format_pct(val):
    """Format percentage."""
    if val >= 0:
        return f"+{val:.1f}%"
    return f"{val:.1f}%"


def print_report(address, stats, top_n=None, sports_only=False, losing_only=False):
    """Print formatted P&L report."""
    print(f"\n{'='*65}")
    print(f"  POLYMARKET P&L — {address[:8]}...{address[-6:]}")
    print(f"{'='*65}\n")

    # Summary
    print(f"  Positions:  {stats['total_positions']} ({stats['open_positions']} open, {stats['closed_positions']} closed)")
    print(f"  Win Rate:   {stats['win_rate']:.1f}% ({stats['winners']}W / {stats['losers']}L)")
    print(f"  Invested:   ${stats['total_invested']:,.2f}")
    print(f"  Cash P&L:   {format_money(stats['total_cash_pnl'])}")
    print(f"  Realized:   {format_money(stats['total_realized_pnl'])}")
    print(f"  Portfolio:  ${stats['total_current_value']:,.2f}")

    # Sport vs Political breakdown
    if stats["sports_positions"] > 0 or stats["political_positions"] > 0:
        print(f"\n  --- By Category ---")
        if stats["sports_positions"] > 0:
            print(f"  Sports:     {stats['sports_positions']} positions, {format_money(stats['sports_pnl'])}")
        if stats["political_positions"] > 0:
            print(f"  Other:      {stats['political_positions']} positions, {format_money(stats['political_pnl'])}")

    # Best/Worst
    if stats["best_trade"]:
        bt = stats["best_trade"]
        print(f"\n  Best Trade:  {format_money(bt['cash_pnl'])} — {bt['title'][:50]}")
    if stats["worst_trade"]:
        wt = stats["worst_trade"]
        print(f"  Worst Trade: {format_money(wt['cash_pnl'])} — {wt['title'][:50]}")

    # Position list
    positions = stats["positions"]
    if sports_only:
        positions = [p for p in positions if p["is_sports"]]
    if losing_only:
        positions = [p for p in positions if p["cash_pnl"] < 0]

    positions.sort(key=lambda x: x["cash_pnl"], reverse=True)

    if top_n:
        positions = positions[:top_n]

    if positions:
        print(f"\n  --- Positions ({len(positions)} shown) ---\n")
        for p in positions:
            status = "OPEN" if p["is_open"] else "DONE"
            sport_tag = " [S]" if p["is_sports"] else ""
            pnl_str = format_money(p["cash_pnl"])
            title = p["title"][:45]
            print(f"  {status:4} {pnl_str:>12}  {p['outcome']:3}@${p['avg_price']:.3f}→${p['cur_price']:.3f}  {title}{sport_tag}")

    print(f"\n{'='*65}\n")


def print_leaderboard(traders, period):
    """Print leaderboard."""
    print(f"\n{'='*65}")
    print(f"  POLYMARKET LEADERBOARD — {period.upper()}")
    print(f"{'='*65}\n")
    print(f"  {'#':>3}  {'Trader':42}  {'P&L':>12}  {'Volume':>12}")
    print(f"  {'─'*3}  {'─'*42}  {'─'*12}  {'─'*12}")

    for i, t in enumerate(traders, 1):
        name = t.get("username") or t.get("name") or t.get("proxyWallet", "")[:12]
        pnl = safe_float(t.get("pnl", t.get("cashPnl", 0)))
        volume = safe_float(t.get("volume", 0))
        addr = t.get("proxyWallet", "")

        display = name if name else f"{addr[:8]}...{addr[-4:]}"
        print(f"  {i:>3}  {display:42}  {format_money(pnl):>12}  ${volume:>10,.0f}")

    print(f"\n  Use: python3 pnl.py <address> to analyze any wallet")
    print(f"{'='*65}\n")


def export_csv(stats, output=None):
    """Export positions to CSV."""
    buf = io.StringIO() if output is None else open(output, "w", newline="")
    writer = csv.writer(buf)
    writer.writerow([
        "title", "outcome", "size", "avg_price", "cur_price",
        "initial_value", "current_value", "cash_pnl", "realized_pnl",
        "percent_pnl", "is_sports", "is_open"
    ])
    for p in stats["positions"]:
        writer.writerow([
            p["title"], p["outcome"], p["size"], p["avg_price"], p["cur_price"],
            p["initial_value"], p["current_value"], p["cash_pnl"], p["realized_pnl"],
            p["percent_pnl"], p["is_sports"], p["is_open"]
        ])
    if output is None:
        print(buf.getvalue())
    else:
        buf.close()
        print(f"Exported to {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket P&L Analyzer — instant wallet breakdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pnl.py 0x1234abcd...          Full P&L report
  python3 pnl.py 0x1234abcd... --top 5  Top 5 positions
  python3 pnl.py 0x1234abcd... --sport  Sports bets only
  python3 pnl.py 0x1234abcd... --csv    CSV export
  python3 pnl.py leaderboard            Top weekly traders
  python3 pnl.py leaderboard --period day  Top daily traders
        """
    )
    parser.add_argument("address", help="Wallet address (0x...) or 'leaderboard'")
    parser.add_argument("--top", type=int, help="Show top N positions only")
    parser.add_argument("--sport", action="store_true", help="Sports positions only")
    parser.add_argument("--losing", action="store_true", help="Losing positions only")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Raw JSON output")
    parser.add_argument("--csv", nargs="?", const=True, dest="csv_out", help="CSV output (optional: filename)")
    parser.add_argument("--period", default="weekly", choices=["daily", "weekly", "monthly", "all"],
                        help="Leaderboard period (default: weekly)")
    parser.add_argument("--limit", type=int, default=20, help="Leaderboard entries (default: 20)")

    args = parser.parse_args()

    # Leaderboard mode
    if args.address.lower() == "leaderboard":
        traders = fetch_leaderboard(args.period, args.limit)
        if not traders:
            print("Error: Could not fetch leaderboard data.", file=sys.stderr)
            sys.exit(1)
        if args.json_out:
            print(json.dumps(traders, indent=2))
        else:
            print_leaderboard(traders, args.period)
        return

    # Wallet analysis mode
    address = args.address
    if not address.startswith("0x"):
        print("Error: Address must start with 0x", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching positions for {address[:10]}...", file=sys.stderr)
    positions = fetch_positions(address)

    if not positions:
        print(f"No positions found for {address}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(positions)} positions. Analyzing...", file=sys.stderr)
    stats = analyze_positions(positions)

    if args.json_out:
        # Clean output for JSON
        output = {
            "address": address,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {k: v for k, v in stats.items() if k != "positions"},
            "positions": stats["positions"],
        }
        print(json.dumps(output, indent=2, default=str))
    elif args.csv_out:
        filename = args.csv_out if isinstance(args.csv_out, str) else None
        export_csv(stats, filename)
    else:
        print_report(address, stats, top_n=args.top, sports_only=args.sport, losing_only=args.losing)


if __name__ == "__main__":
    main()
