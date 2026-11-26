---
name: trade-backtest
description: >-
  Trade Backtest. Replays the paper desk's exact trade on each ticker's last ~60 sessions of
  5-minute bars: a buy-stop over the opening-range high, a stop at the range low but at least
  0.25x the daily ATR, half the shares off at +1R with the rest moved to breakeven, the other
  half at 2R, 3R or 4R (the best kept), out by 3:55 PM. After the close it ranks tomorrow's
  shortlist and drops the names whose rule lost money. Use when the user says "backtest the
  shortlist", "which of these have worked", "backtest WMT", "check the shortlist after the
  close", or "/trade-backtest". Never places an order.
argument-hint: "[--shortlist trader/shortlist.json --drop-losers | --symbols A,B]"
---

# trade-backtest

`${CLAUDE_SKILL_DIR}` below is this skill's folder.

```bash
python "${CLAUDE_SKILL_DIR}/backtest.py" --shortlist trader/shortlist.json --drop-losers
python "${CLAUDE_SKILL_DIR}/backtest.py" --symbols WMT,PDD
python "${CLAUDE_SKILL_DIR}/backtest.py" --symbols WMT --json
```

Run it from the project root. One Yahoo request per ticker (60 days of 5-minute bars), about
a second each; results are cached per ticker for the day in `trader/backtest/<date>/`.

## The rule it replays (the desk's trade)

| step | rule | from `trader/config.json` |
| --- | --- | --- |
| range | the first `or_minutes` of the session | `scout.or_minutes` (5) |
| entry | buy-stop one cent over the range high, live from 9:45 to 15:30; fills at that price, or at the bar's open if it opens above (skipped if more than 1 % above) | `no_entries_before`, `no_entries_after` |
| stop | the range low, but at least `min_stop_atr` x the daily ATR(14) under the entry | `scout.min_stop_atr` (0.25) |
| T1 | half the shares at entry + 1R; the other half's stop moves to the entry | |
| T2 | the other half at entry + 2R, 3R or 4R: each is tested, the best average R kept | |
| close | anything left is sold at 15:55 | `flat_by` |

Ties inside a 5-minute bar are read against the trade: the stop comes before any target in
the same bar, and the fill bar never takes a target.

## Verdicts

- **keep**: at least `--min-trades` (5) trades and an average R above zero at its best T2.
- **thin**: fewer trades than that. Kept, ranked after the keeps: no evidence either way.
- **drop**: the average R at its best T2 is zero or less.

`--drop-losers` rewrites the shortlist: kept names best first with their `backtest` numbers,
then thin ones, then any name the backtest could not fetch (kept, unranked). The dropped
names are listed under `dropped`.

## Reading it honestly

- Sixty sessions is a small sample, and picking the best of three T2s on the same sample
  flatters it: treat a small positive average as "not clearly broken", not as an edge.
- Real fills are worse than the replay, most of all at the open.
- It tests every breakout, without the scout's stocks-in-play, VWAP or news gates, so it
  measures the stock's breakout behaviour, not the full scout.
- Paper research only. Never places an order.
