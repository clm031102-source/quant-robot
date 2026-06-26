# CN Stock Round299 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round299-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round299 completed the first shard18 source-construction batch after the Round296-298 review. It produced no factor names, no IC screens, no portfolio grids, and no promotable candidates. This remains intentional: aggregate financial reporting timeliness coverage is now 379 unique symbols, still below the 1,000-symbol source gate required before candidate generation.

The useful work was:

- read and followed the Round296-298 review before endpoint spend;
- previewed shard18 offset0 and offset5 before live requests;
- skipped already-covered symbols before backfill;
- backfilled 7 net-new symbols across split subsegments;
- increased aggregate source coverage from 372 to 379 unique symbols;
- confirmed 6 of 7 net-new symbols pass both required statement column groups;
- blocked `601336.SH` from full asset-growth usage because its balance-sheet current-asset fields were absent/non-null incomplete;
- fixed a reporting bug where the shard backfill top-level summary could pass based on readiness while final ingest quality failed.

## Startup Gate

Round299 started from the completed Round298 state.

| Item | Result |
|---|---|
| Quant PM startup gate | ready |
| Primary project market | CN_ETF remains primary downstream strategy scope |
| This run scope | CN stock factor validation/source construction |
| CN stock startup gate | cleared |
| CN stock data manifest | review_required, no hard blockers |
| Candidate generation | blocked until 1,000 unique symbols |

The manifest warnings remain:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

These warnings do not block this statement-source backfill, but they remain hard review items before any future factor matrix or promotion claim.

## Pre-Run Review

Round299 first read:

```text
docs/research/cn_stock_round296_298_three_round_review_2026-06-26.md
```

The review required:

- continue financial reporting timeliness source construction;
- run aggregate overlap preview before live endpoint spend;
- scan ahead if the preview net-new ratio is below 80%;
- split around known existing symbols;
- keep stock-basic pre-listing filtering enabled;
- keep candidate generation blocked until at least 1,000 unique symbols clear the source gate.

## Overlap Preview

Round299 first previewed shard18 offset0 limit5.

| Preview | Existing Symbols | Net-New Symbols | Net-New Ratio | Decision |
|---|---:|---:|---:|---|
| shard18 offset0 limit5 | 2 | 3 | 60% | scan ahead and split |
| shard18 offset5 limit5 | 1 | 4 | 80% | backfill net-new symbols |

Existing symbols skipped before live requests:

```text
000021.SZ
000036.SZ
000422.SZ
```

Net-new symbols identified:

```text
601336.SH
600834.SH
000882.SZ
002043.SZ
000735.SZ
300159.SZ
300148.SZ
```

## Backfill Result

Round299 backfilled only the net-new symbols with stock-basic pre-listing filtering enabled.

| Segment | Symbols | Active Symbol-Periods | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Required Groups | Passes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| shard18 offset0 limit1 | 1 | 44 | 132 | 44 | 2 | 0 | 1 / 2 | false |
| shard18 offset3 limit2 | 2 | 88 | 264 | 88 | 0 | 0 | 2 / 2 | true |
| shard18 offset5 limit3 | 3 | 132 | 396 | 135 | 2 | 3 | 2 / 2 | true |
| shard18 offset9 limit1 | 1 | 44 | 132 | 44 | 1 | 0 | 2 / 2 | true |
| total | 7 | 308 | 924 | 311 | 5 | 3 | mixed | mixed |

Quality-passing net-new symbols:

```text
600834.SH
000882.SZ
002043.SZ
000735.SZ
300159.SZ
300148.SZ
```

Quality-blocked net-new symbol:

```text
601336.SH
```

## Quality Issue

`601336.SH` has a final ingest quality blocker:

```text
missing_required_financial_column_group:asset_growth_quality
```

The `accounting_accrual_quality` group is usable, but the `asset_growth_quality` group is not fully usable because `total_cur_assets` and `total_cur_liab` did not provide non-null coverage in this subsegment. This symbol must be excluded from asset-growth-quality factor construction or repaired before it contributes to that family.

## Reporting Bug Fixed

Round299 exposed a second quality-reporting issue. The shard-level backfill `summary` used the PIT readiness audit as the top-level pass/fail gate. PIT readiness checks file structure and PIT date availability, but the final ingest quality report checks actual non-null required column groups.

Root cause:

- `readiness.summary.passes` was true because the processed file had the required columns and PIT dates;
- `ingest.summary.passes` was false because one required column group had no non-null current-asset/current-liability coverage;
- the top-level `summary.passes` copied readiness and incorrectly reported the subsegment as passed.

Fix:

- top-level `summary.passes` now requires both final ingest quality and readiness to pass;
- top-level `required_column_groups_passing` now comes from final ingest quality when available;
- `quality_blockers`, `readiness_blockers`, and merged `blockers` are recorded separately.

Regression coverage:

```text
tests.unit.test_financial_statement_shard_backfill_cli.FinancialStatementShardBackfillCliTests.test_top_level_summary_uses_final_ingest_quality_gate
```

## Aggregate Source Gate

After Round299, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 108 |
| Aggregate rows | 81,496 |
| Unique symbols | 379 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 372 to 379 unique symbols, but this is still only 37.9% of the 1,000-symbol source gate.

## Factor Outcome

Round299 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is deliberate source construction, not alpha discovery. Candidate generation remains blocked until the long-cycle PIT source has enough market coverage.

## Next Direction

Round300 should continue source construction from shard18 offset10, with the same hard controls:

- run overlap preview before live endpoint spend;
- scan ahead if net-new ratio is below 80%;
- split around existing symbols;
- use stock-basic pre-listing filtering;
- treat empty responses and duplicate rows as quality watch items;
- keep candidate generation blocked until 1,000 unique symbols pass the source gate.

Next allowed direction:

```text
round300_continue_financial_reporting_timeliness_backfill_on_shard18_offset10_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```
