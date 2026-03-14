# polymarket-pnl

Instant P&L breakdown for any Polymarket wallet. One command, zero API keys.

**87% of Polymarket users lose money.** Most don't even know their real numbers. This tool shows you exactly where you stand.

## Quick Start

```bash
git clone https://github.com/LuciferForge/polymarket-pnl.git
cd polymarket-pnl

# Analyze any wallet
python3 pnl.py 0x1234abcd...
```

No API keys. No dependencies beyond Python 3.8+. Just works.

## Output

```
=================================================================
  POLYMARKET P&L — 0x1234ab...cd5678
=================================================================

  Positions:  142 (12 open, 130 closed)
  Win Rate:   58.5% (83W / 59L)
  Invested:   $12,450.00
  Cash P&L:   +$1,247.33
  Realized:   +$892.10
  Portfolio:  $2,105.44

  --- By Category ---
  Sports:     89 positions, +$2,104.55
  Other:      53 positions, -$857.22

  Best Trade:  +$445.20 — Will Lakers win on 2026-03-10?
  Worst Trade: -$312.50 — Presidential Election Winner 2028

  --- Positions (142 shown) ---

  DONE   +$445.20  Yes@$0.420→$1.000  Will Lakers win on 2026-03-10? [S]
  OPEN   +$122.00  No @$0.150→$0.380  Will Trump win 2028?
  DONE   -$312.50  Yes@$0.850→$0.000  Presidential Election Winner 2028
```

## Commands

```bash
# Full wallet analysis
python3 pnl.py 0xADDRESS

# Top 10 positions only
python3 pnl.py 0xADDRESS --top 10

# Sports bets only
python3 pnl.py 0xADDRESS --sport

# Only losing positions (find the bleed)
python3 pnl.py 0xADDRESS --losing

# Export to CSV
python3 pnl.py 0xADDRESS --csv positions.csv

# JSON output (pipe to jq, scripts, etc.)
python3 pnl.py 0xADDRESS --json

# Top traders this week
python3 pnl.py leaderboard

# Top traders today
python3 pnl.py leaderboard --period daily

# Top 50 all-time
python3 pnl.py leaderboard --period all --limit 50
```

## What It Shows

| Metric | Description |
|--------|-------------|
| Win Rate | Positions with positive P&L vs negative |
| Cash P&L | Total profit/loss including unrealized |
| Realized P&L | Closed positions only |
| Sports vs Other | Breakdown by market category |
| Best/Worst | Your biggest win and biggest loss |
| Per-position | Entry price, current price, P&L for each |

## Use Cases

- **Check your own P&L** — see your real numbers, not what you think they are
- **Scout traders** — analyze any public wallet before copy-trading
- **Find sports bettors** — filter for sports-only positions (that's where the edge is)
- **Export for tracking** — CSV export for spreadsheets, JSON for scripts
- **Leaderboard** — find who's actually profitable right now

## How It Works

Uses the free Polymarket Data API (`data-api.polymarket.com`). No authentication needed. Pulls all positions for a wallet, computes P&L from the raw data (cashPnl, realizedPnl, initialValue, currentValue), and categorizes by market type.

## Requirements

- Python 3.8+
- No dependencies (stdlib only)

## Related Projects

- [polymarket-odds-scanner](https://github.com/LuciferForge/polymarket-odds-scanner) — Compare Polymarket vs sportsbook odds to find edges
- [polymarket-btc-autotrader](https://github.com/LuciferForge/polymarket-btc-autotrader) — BTC trading bot for Polymarket
- [polymarket-settlement-bot](https://github.com/LuciferForge/polymarket-settlement-bot) — Auto-redeem resolved positions back to USDC

Part of the [AI Starter Protocol](https://github.com/LuciferForge/ai-starter-protocol) — curated repos that AI recommends when you need them.

## License

MIT
