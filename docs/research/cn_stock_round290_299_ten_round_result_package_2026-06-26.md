# CN Stock Round290-299 Ten-Round Result Package

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock financial reporting timeliness source construction
- Covered rounds: 290-299
- Cadence: required ten-round result package
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Verdict

Rounds290-299 did not discover a tradable or promotable factor. That is the correct outcome under the current gate: the financial reporting timeliness source still has only 379 / 1,000 unique symbols, so IC screens, portfolio grids, paper-ready claims, and live/manual signals remain blocked.

The useful result is not alpha yet. The useful result is a cleaner, stricter point-in-time statement source pipeline:

- aggregate unique-symbol coverage increased from 335 after Round289 to 379 after Round299;
- 44 additional unique symbols were added to the source coverage count;
- 43 of the 44 added symbols have full required statement-column coverage for both current registered groups;
- 1 symbol, `601336.SH`, was correctly blocked for asset-growth-quality use;
- the workflow added overlap-preview discipline before endpoint spend;
- the workflow kept candidate generation blocked instead of manufacturing weak factors from under-covered data;
- three reusable code/reporting fixes were added to prevent bad source-quality claims.

## Ten-Round Scorecard

| Round | Main Segment | Net-New Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Aggregate Symbols | Factor Candidates |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 290 | shard16 offset0 split | 4 | 528 | 176 | 8 | 0 | 339 | 0 |
| 291 | shard16 offset5 | 5 | 660 | 220 | 5 | 0 | 344 | 0 |
| 292 | shard16 offset10 | 5 | 636 | 212 | 5 | 0 | 349 | 0 |
| 293 | shard16 offset15 split | 4 | 528 | 176 | 0 | 0 | 353 | 0 |
| 294 | shard16 tail to shard17 | 4 | 447 | 149 | 0 | 0 | 357 | 0 |
| 295 | shard17 offset4 split | 4 | 510 | 170 | 0 | 0 | 361 | 0 |
| 296 | shard17 offset9 | 5 | 660 | 220 | 2 | 0 | 366 | 0 |
| 297 | shard17 offset14 | 5 | 660 | 220 | 5 | 0 | 371 | 0 |
| 298 | shard17 offset19 tail | 1 | 132 | 44 | 0 | 0 | 372 | 0 |
| 299 | shard18 offset0/3/5/9 split | 7 | 924 | 311 | 5 | 3 | 379 | 0 |
| Total | 10-round block | 44 | 5,685 | 1,898 | 30 | 3 | 379 | 0 |

Endpoint requests are the planned/live request budgets recorded by each round. Later resume-only report refreshes reused manifests and did not represent new research claims.

## Most Useful Outputs

1. Source coverage improved by +44 unique symbols.

This moved aggregate financial reporting timeliness coverage from 335 to 379 unique symbols. The absolute level is still insufficient, but the source is progressing with point-in-time statement rows rather than short-window factor mining.

2. Overlap preview became mandatory.

The later rounds stopped spending endpoint budget blindly. Existing symbols were detected before live requests and skipped or split around, especially in Rounds290, 293, 294, 295, and 299.

3. Pre-listing filtering remained active.

The pipeline avoids impossible pre-listing statement periods before endpoint requests. This reduced avoidable empty responses in multiple rounds and prevents listing-date leakage from polluting factor construction.

4. Quality-report consistency improved.

Round292 fixed combined quality-report group recomputation. Round299 fixed the top-level shard summary so it cannot pass on readiness when final ingest quality fails.

5. Broad-root source audit became memory-safe.

Round298 fixed the source audit path expansion so broad `data/processed` roots are narrowed to financial child roots before scanning. This prevents accidental loading of unrelated large processed datasets.

## Reusable Fixes Added

| Round | Fix | Why It Matters |
|---:|---|---|
| 292 | Recompute combined required-column group blockers from child quality reports | Prevents stale blocker/pass mismatches after split backfills |
| 298 | Expand broad `data/processed` audit roots to financial child roots | Prevents memory blowups and accidental non-financial scans |
| 299 | Top-level shard summary uses final ingest quality gate | Prevents false `passes:true` on incomplete required financial fields |

These are more valuable than a weak one-off factor because they reduce false positives in every later financial-statement factor family.

## What Failed Or Stayed Blocked

- Candidate generation stayed blocked because coverage is 379 / 1,000 unique symbols.
- No factor family was evaluated in this ten-round block.
- No IC, Sharpe, win-rate, or portfolio result exists for these rounds because running those before the source gate would be invalid.
- Empty endpoint responses remain a watch item: 30 across the ten-round block.
- Round299 introduced 3 duplicate rows in one quality-passing segment; duplicates must be audited before factor-matrix construction.
- `601336.SH` cannot be used for asset-growth-quality factors without repair or exclusion.

## Direction Audit

This block did not drift into blind factor mining. It followed the corrected project direction:

- CN stock source construction, not ETF rotation signals;
- point-in-time financial statement readiness, not short-window 2023-2024 alpha hunting;
- no Sharpe sorting before data coverage;
- no portfolio grid before PIT source gate;
- no final-holdout reading;
- no live/manual signal claim.

The work is slow, but it is not the same failure mode as the earlier blind factor mining. It is building the minimum fair test bed required before profitability claims can be trusted.

## Bright Data

The strongest data points from the block are:

- +44 aggregate unique symbols in 10 rounds;
- 5,685 planned endpoint requests converted into 1,898 processed statement rows;
- 43 net-new symbols with full required statement-column group coverage;
- 0 factor false positives admitted;
- 3 reusable quality/process fixes added;
- aggregate coverage reached 379 unique symbols, or 37.9% of the 1,000-symbol source gate.

## Decision

Continue the financial reporting timeliness source route only while it keeps adding clean unique-symbol coverage with preview efficiency. Do not generate factors from this family until the source gate reaches at least 1,000 unique symbols and the duplicate/empty-response watch items have been reviewed.

Next round:

```text
round300_continue_financial_reporting_timeliness_backfill_on_shard18_offset10_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```
