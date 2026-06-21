# CN Stock Tushare Fina Indicator First10 Shard Smoke Round94 - 2026-06-22

## Executive Summary

Round94 produced no new factor and no profitability claim. It ran the first 10 symbols from the Round93 `fina_indicator` shard plan across the full 2015-2025 quarterly period range, then fixed a real same-key financial-row duplication issue found in the smoke.

The useful result is that shard-based financial backfill is now executable, resumable, and protected against both exact duplicate rows and same-key restatement-style rows.

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks, not ETF rotation
- Source shard plan: `data/reports/fina_indicator_symbol_shard_plan_round93_20260621/fina_indicator_symbol_shard_plan.json`
- Shard: 1
- Selected symbols: first 10 symbols from shard 1
- Periods: 44 quarterly periods from `20150331` through `20251231`
- Safety: research-to-review only; no broker, account, order, or live-trading action

Selected symbols:

```text
000001.SZ, 000002.SZ, 000004.SZ, 000006.SZ, 000007.SZ,
000008.SZ, 000009.SZ, 000010.SZ, 000011.SZ, 000012.SZ
```

## What Was Built

Code:

- Added `scripts/run_fina_indicator_shard_backfill_smoke.py`.
- The new entrypoint reads a shard plan, selects shard `N`, takes first `max_symbols`, runs the existing limited-symbol backfill smoke, then runs PIT readiness.
- Added same-key financial-row deduplication after date normalization:
  - key: `symbol + ann_date + end_date`;
  - policy: keep the last returned row.

Tests:

- Added `tests/unit/test_fina_indicator_shard_backfill_smoke_cli.py`.
- Added a regression test for non-exact same-key financial rows.

## Live Smoke Result

Command:

```powershell
python scripts\run_fina_indicator_shard_backfill_smoke.py --shard-plan-json data\reports\fina_indicator_symbol_shard_plan_round93_20260621\fina_indicator_symbol_shard_plan.json --shard-id 1 --max-symbols 10 --batch-size 20 --max-requests 440 --output-dir data\processed\tushare_fina_indicator_shard1_first10_backfill_smoke_round94_20260622 --pit-readiness-output-dir data\reports\tushare_financial_pit_readiness_round94_shard1_first10_20260622
```

First live run:

| Metric | Value |
|---|---:|
| Selected symbols | 10 |
| Periods | 44 |
| Planned requests | 440 |
| Downloaded raw partitions | 440 |
| Runtime | about 9m54s |
| Initial processed rows | 430 |
| Initial duplicate rows | 1 |
| Empty requests | 11 |
| PIT readiness | pass |

The initial duplicate was not an exact duplicate. It was:

| Symbol | Report Period | Announcement Date | Difference |
|---|---|---|---|
| `000001.SZ` | 2024-06-30 | 2024-08-16 | two rows differed only in `ocfps`: 5.8602 versus 5.8600 |

After the same-key deduplication fix, the same command was rerun against existing raw partitions. It skipped all 440 raw requests and rebuilt processed output locally.

Final result:

| Metric | Value |
|---|---:|
| Selected symbols | 10 |
| Periods | 44 |
| Requests | 440 |
| Skipped requests on refresh | 440 |
| Processed rows | 429 |
| Empty requests | 11 |
| Duplicate rows | 0 |
| Assets | 10 |
| Ann date range | 2015-04-24 to 2026-04-29 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Missing asset id rows | 0 |
| Missing numeric rows | 86 |
| Missing numeric columns | `grossprofit_margin`: 43, `roa`: 43 |

Empty requests:

```text
000010.SZ:20150331
000012.SZ:20160930
000001.SZ:20170930
000007.SZ:20180630
000011.SZ:20190331
000008.SZ:20190630
000011.SZ:20190630
000002.SZ:20201231
000006.SZ:20210630
000011.SZ:20230630
000011.SZ:20241231
```

## PIT Readiness

Final readiness summary:

| Metric | Value |
|---|---:|
| Passes | true |
| Blockers | 0 |
| Files scanned | 456 |
| Financial-like datasets | 452 |
| PIT-ready datasets | 452 |

## Research Decision

Round94 is accepted as data-pipeline progress, not factor progress.

Current factor status:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New Round94 factor candidates: 0

Do not pre-register profitability factors from this first10 smoke. Ten symbols are still too narrow for cross-sectional profitability research and would create survivorship and sample-size risk.

## Next Direction

Round95 should run the full shard 1 backfill:

```text
100 symbols * 44 periods = 4,400 requests
```

Required gates after Round95:

- runtime recorded;
- empty-response rate reported;
- duplicate rows = 0;
- missing asset id rows = 0;
- PIT readiness passes;
- no profitability factor pre-registration if any quality gate fails.

Only after at least one clean full 100-symbol shard should the project consider pre-registering profitability-quality factor candidates.
