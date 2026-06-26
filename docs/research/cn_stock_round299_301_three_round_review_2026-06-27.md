# CN Stock Round299-301 Three-Round Review

- Date: 2026-06-27
- Machine: office_desktop
- Scope: CN A-share stock financial reporting timeliness source construction
- Covered rounds: 299-301
- Cadence: required three-round review after Round301
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Verdict

Rounds299-301 produced 0 promotable factors, 0 paper-ready candidates, and 0 live/manual signals. That is the correct outcome under the current gate: financial reporting timeliness coverage is now 388 / 1,000 unique symbols, so IC screens, portfolio grids, Sharpe/win-rate claims, and live signals remain blocked.

The useful result is source construction and process tightening:

- aggregate unique-symbol coverage increased from 372 after Round298 to 388 after Round301;
- 16 additional unique symbols were added across the three-round block;
- 15 of 16 net-new symbols passed the currently required statement-column groups;
- `601336.SH` was correctly blocked for asset-growth-quality use in Round299;
- overlap preview skipped existing symbols before endpoint spend in Rounds299 and 301;
- Round299 fixed a top-level shard-summary bug that could have overstated source quality;
- Round301 completed shard18 and prepared shard19 with a guarded throughput improvement.

## Three-Round Scorecard

| Round | Main Segment | Net-New Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Aggregate Symbols | Factor Candidates |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 299 | shard18 offset0/3/5/9 split | 7 | 924 | 311 | 5 | 3 | 379 | 0 |
| 300 | shard18 offset10 | 5 | 660 | 220 | 2 | 0 | 384 | 0 |
| 301 | shard18 offset15/17 split | 4 | 528 | 176 | 2 | 0 | 388 | 0 |
| Total | 3-round block | 16 | 2,112 | 707 | 9 | 3 | 388 | 0 |

## What Worked

1. Coverage kept improving.

The source moved from 372 to 388 unique symbols. This is still not enough, but the work is adding real PIT statement coverage rather than producing short-sample factor noise.

2. Overlap preview saved endpoint budget.

Round299 skipped `000021.SZ`, `000036.SZ`, and `000422.SZ` before live requests. Round301 skipped `000078.SZ` before live requests and split the backfill around it.

3. Quality gates rejected partial financial usage.

Round299 did not let `601336.SH` enter asset-growth-quality factor construction because required balance-sheet current-asset/current-liability fields were incomplete. That is the right failure mode.

4. Duplicate rows improved after Round299.

Round299 had 3 duplicate rows. Rounds300 and 301 both had 0 duplicate rows. Duplicate rows remain a watch item before any factor matrix build, but the immediate direction is cleaner.

5. Candidate generation stayed blocked.

The project did not claim IC, Sharpe, win rate, or profitability from a 388-symbol partial source. This protects the project from the earlier failure mode: optimizing parameters on incomplete data and then presenting backtest artifacts as alpha.

## What Is Still Weak

- Coverage is only 388 / 1,000, or 38.8% of the minimum source gate.
- At the recent 4-5 clean symbols per round pace, reaching 1,000 would take too many rounds.
- Empty endpoint responses remain a small but persistent watch item: 9 across this three-round block.
- Round299 duplicate rows must be resolved or isolated before any factor matrix uses the affected source.
- There are still 0 source-ready roots in the aggregate audit.

## Direction Audit

This block did not drift back into blind factor mining. It stayed aligned with the corrected project direction:

- CN stock source construction, not ETF rotation;
- point-in-time financial statement timing, not 2023-2024 short-window mining;
- no candidate generation before source readiness;
- no final-holdout tuning;
- no live/manual signal claim.

The main efficiency problem is throughput. The next round should test a small, controlled increase in batch size from 5 to 6 symbols where preview evidence supports it. This is not a relaxation of quality standards; it is only an endpoint-efficiency probe under the same overlap, pre-listing, empty-response, duplicate-row, and quality-report gates.

## Decision

Continue financial reporting timeliness source construction for Round302, because the data source remains accessible and clean enough to keep building. Do not generate financial reporting timeliness candidates until the aggregate source gate reaches at least 1,000 unique symbols and duplicate/empty-response watch items are reviewed.

Next allowed direction:

```text
round302_continue_financial_reporting_timeliness_backfill_on_shard19_offset0_limit6_efficiency_probe_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```

Round302 requirements:

- start from shard19 offset0;
- preview before live endpoint spend;
- use `symbol-limit 6` only if preview confirms enough net-new symbols and endpoint budget remains controlled;
- split around any existing symbols;
- keep stock-basic pre-listing filtering enabled;
- keep candidate generation blocked until 1,000 unique symbols pass the source gate.
