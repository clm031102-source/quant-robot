# CN Stock Tushare Fina Indicator Limited Backfill Smoke Round92 - 2026-06-21

## Executive Summary

Round92 produced no new factor and no profitability claim. It advanced the financial-data path from a planning-only step to a real limited-symbol long-history `fina_indicator` smoke covering 2015-03-31 through 2025-12-31.

The important result is that the project can now run a resume-safe symbol-scoped financial indicator backfill, record empty responses without aborting, deduplicate exact duplicate financial rows, and pass the PIT readiness audit on the resulting local dataset.

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks, not ETF rotation
- Symbols: `000001.SZ`, `600519.SH`
- Periods: 44 quarterly report periods from `20150331` through `20251231`
- Safety: research-to-review only; no broker, account, order, or live-trading action

## What Was Built

Code:

- Added `empty_response_policy="record"` to `run_tushare_fina_indicator_ingest(...)`.
- Kept default empty-response behavior as `fail`.
- Resume now skips completed zero-row raw partitions.
- Exact duplicate financial rows are removed before processed output.
- Added `scripts/run_fina_indicator_limited_backfill_smoke.py`.

Tests:

- Empty-response record policy.
- Resume skip for recorded zero-row requests.
- Exact duplicate financial-row deduplication.
- Limited backfill smoke CLI report and request-budget gate.

## Real Smoke Result

Command:

```powershell
python scripts\run_fina_indicator_limited_backfill_smoke.py --symbols 000001.SZ,600519.SH --start-period 2015-03-31 --end-period 2025-12-31 --batch-size 20 --max-requests 100 --output-dir data\processed\tushare_fina_indicator_limited_backfill_smoke_round92_20260621
```

Final smoke summary after deduplication refresh:

| Metric | Value |
|---|---:|
| Symbols | 2 |
| Periods | 44 |
| Planned requests | 88 |
| Processed rows | 79 |
| Empty requests | 9 |
| Skipped requests on refresh | 88 |
| Duplicate rows | 0 |
| Assets | 2 |
| Ann date range | 2015-04-21 to 2026-04-17 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Missing asset id rows | 0 |
| Missing numeric rows | 78 |
| Missing numeric columns | `grossprofit_margin`: 39, `roa`: 39 |

The first live run downloaded the planned requests. After the exact-duplicate deduplication fix, the same command was rerun against the existing manifest/raw partitions. It skipped all 88 requests and rebuilt processed output locally, reducing processed rows from 144 to 79 and duplicate rows from 65 to 0.

## PIT Readiness

Command:

```powershell
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\tushare_fina_indicator_limited_backfill_smoke_round92_20260621 --output-dir data\reports\tushare_financial_pit_readiness_round92_limited_smoke_20260621
```

Readiness summary:

| Metric | Value |
|---|---:|
| Passes | true |
| Blockers | 0 |
| Files scanned | 103 |
| Financial-like datasets | 100 |
| PIT-ready datasets | 100 |

## Research Decision

Round92 is accepted as data-pipeline progress, not factor progress.

Current factor status remains:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New Round92 factor candidates: 0

## Important Caveats

- The smoke used only two long-lived stocks, so it does not prove full-universe coverage.
- `roa` and `grossprofit_margin` are missing for many rows, likely because banks and some financial firms do not report those metrics in the same way as industrial firms.
- A full current-symbol universe still implies more than 240,000 symbol-period requests, so the next step must be a shard/budget plan, not a direct full-universe run.

## Next Direction

Round93 should build a symbol-universe and shard plan for a larger `fina_indicator` backfill:

- choose the exact symbol universe from local `stock_basic` and/or clean tradable bars;
- split requests into deterministic shards;
- estimate request counts per shard;
- preserve resume and empty-response recording;
- require PIT readiness and duplicate-row quality gates after each shard;
- still block profitability-factor pre-registration until enough financial-history coverage exists.
