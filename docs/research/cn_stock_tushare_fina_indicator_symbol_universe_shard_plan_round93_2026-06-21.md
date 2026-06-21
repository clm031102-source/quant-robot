# CN Stock Tushare Fina Indicator Symbol Universe Shard Plan Round93 - 2026-06-21

## Executive Summary

Round93 produced no new factor and no profitability claim. It created the first compact broad-universe shard plan for Tushare `fina_indicator` long-history backfill, using local `stock_basic` metadata and excluding BJ symbols for the first broad pass.

The point of this round is cost control. A full current-symbol backfill is large enough that direct execution would be wasteful and hard to audit.

## Scope

- Source universe: `data/processed/cn_stock_metadata/metadata/tushare_stock_basic`
- Excluded suffixes: `BJ`
- Periods: 44 quarterly periods from `20150331` through `20251231`
- Symbols per shard: 100
- Max requests per shard: 4,400
- Safety: planning only; no Tushare calls; no raw/processed data generated

## Shard Plan Result

Command:

```powershell
python scripts\run_fina_indicator_symbol_shard_plan.py --stock-basic-root data\processed\cn_stock_metadata\metadata\tushare_stock_basic --start-period 2015-03-31 --end-period 2025-12-31 --symbols-per-shard 100 --max-requests-per-shard 4400 --exclude-suffixes BJ --output-dir data\reports\fina_indicator_symbol_shard_plan_round93_20260621
```

Summary:

| Metric | Value |
|---|---:|
| Included symbols | 5,208 |
| Excluded BJ symbols | 321 |
| Quarterly periods | 44 |
| Total planned requests | 229,152 |
| Shard count | 53 |
| Requests per full shard | 4,400 |
| Last shard requests | 352 |
| Blockers | 0 |

First shards:

| Shard | Symbols | Requests | First Symbol | Last Symbol |
|---:|---:|---:|---|---|
| 1 | 100 | 4,400 | `000001.SZ` | `000516.SZ` |
| 2 | 100 | 4,400 | `000517.SZ` | `000669.SZ` |
| 3 | 100 | 4,400 | `000670.SZ` | `000820.SZ` |

Last shard:

| Shard | Symbols | Requests | First Symbol | Last Symbol |
|---:|---:|---:|---|---|
| 53 | 8 | 352 | `688811.SH` | `689009.SH` |

## Decision

Do not start the full 53-shard backfill yet.

The Round92 real smoke took roughly minutes for 88 requests. A 4,400-request full shard could run for hours and should not be launched before a smaller first-shard smoke proves runtime, empty-response rate, duplicate rate, and PIT readiness behavior on a broader symbol mix.

## Next Direction

Round94 should run the first 10 symbols from shard 1 across the full 44-quarter period:

- expected requests: 10 symbols * 44 periods = 440 requests;
- use `empty_response_policy="record"`;
- use resume;
- run PIT readiness after the smoke;
- require duplicate rows = 0 before any larger shard attempt;
- still do not pre-register profitability factors.

Current factor status remains:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New Round93 factor candidates: 0
