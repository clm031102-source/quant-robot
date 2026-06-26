# CN Stock Round298 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round298-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round298 completed the tail of shard17. It produced no factor names, no IC screens, no portfolio grids, and no promotable candidates. This remains intentional: aggregate financial reporting timeliness coverage is now 372 unique symbols, still below the 1,000-symbol minimum required before candidate generation.

The useful work was:

- ran the Quant PM and CN stock startup gates before endpoint spend;
- previewed shard17 offset19 limit5 before live requests;
- confirmed the only remaining shard17 symbol was net-new;
- backfilled 1 net-new PIT statement symbol;
- increased aggregate source coverage from 371 to 372 unique symbols;
- kept empty requests at 0, duplicate rows at 0, and required financial column groups at 2 / 2;
- fixed the aggregate source-audit execution path so broad `data/processed` roots do not accidentally load non-financial parquet files;
- completed the required Round296-298 review after this round.

## Startup Gate

Round298 started from the completed Round297 state.

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

These do not block this statement-source backfill, but they still need explicit handling before future factor promotion.

## Pre-Run Overlap Preview

Round298 previewed shard17 offset19 limit5.

| Metric | Value |
|---|---:|
| Shard id | 17 |
| Symbol offset | 19 |
| Symbol limit | 5 |
| Financial roots scanned | 103 |
| Existing symbols | 0 |
| Net-new symbols | 1 |
| Net-new ratio | 100% |

Preview symbols:

```text
000669.SZ
```

Because the only selected symbol was net-new, the live batch stayed at shard17 offset19 limit5.

## Backfill Result

Round298 backfilled the one net-new symbol with stock-basic pre-listing filtering enabled.

| Metric | Value |
|---|---:|
| Planned symbol-periods | 44 |
| Active symbol-periods | 44 |
| Pre-listing symbol-periods skipped | 0 |
| Pre-listing endpoint requests avoided | 0 |
| Endpoint count | 3 |
| Endpoint requests | 132 |
| Processed rows | 44 |
| Empty requests | 0 |
| Duplicate rows | 0 |
| Required column groups passing | 2 / 2 |
| Readiness blockers | 0 |
| Quality report assets | 1 |
| Quality report rows | 44 |
| Quality report passes | true |

Net-new symbol:

```text
000669.SZ
```

Quality date coverage:

| Field | Range |
|---|---|
| Announcement date | 2015-04-24 to 2026-04-29 |
| Report period | 2015-03-31 to 2025-12-31 |

## Aggregate Source Gate

After Round298, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 104 |
| Aggregate rows | 79,950 |
| Unique symbols | 372 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 371 to 372 unique symbols. This is 37.2% of the 1,000-symbol source gate.

## Source-Audit Execution Fix

The first aggregate audit attempt incorrectly passed the entire `data/processed` directory as a single financial root. That caused the audit loader to read non-financial parquet files and fail in `pd.concat` with an 869 MiB allocation error.

The reusable fix is now in the project:

- the audit loader reads only the minimal timeliness columns required for source coverage: `symbol` or `ts_code` or `asset_id`, plus `ann_date` and `end_date`;
- the CLI expands a broad `data/processed` root into matching `financial_statement` and `financial_pit_signal` child roots;
- a regression test covers the processed-root expansion and ignores unrelated daily-bar parquet files.

## Factor Outcome

Round298 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is the correct outcome. Testing financial reporting timeliness at 372 symbols would still be underpowered and vulnerable to false positives.

## Decision For Round299

Continue source construction, not candidate generation.

Next allowed direction:

```text
round299_start_with_round296_298_three_round_review_then_continue_financial_reporting_timeliness_backfill_on_shard18_offset0_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```

Round299 requirements:

- read the Round296-298 three-round review first;
- preview shard18 offset0 before any live request;
- scan ahead if preview net-new ratio is below 80%;
- split around existing symbols before live requests;
- keep stock-basic pre-listing filtering mandatory;
- verify standard quality report summaries against recomputed required-column groups;
- track empty requests and duplicate rows;
- keep candidate generation blocked until the 1,000-symbol source gate clears.
