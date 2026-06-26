# CN Stock Round292-294 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock financial reporting timeliness source construction
- Review cadence: required every 3 rounds
- Reviewed rounds: 292, 293, 294
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Verdict

Rounds292-294 correctly produced no factors. The aggregate financial reporting timeliness source reached only 357 / 1,000 unique symbols, so IC screens, portfolio grids, paper-ready claims, and live/manual signals remain blocked.

The direction remains useful as source construction, not alpha discovery yet. The route improved clean point-in-time statement coverage, fixed a quality-report reliability issue, and kept endpoint spend disciplined with overlap preview, split-around-existing-symbols, and stock-basic pre-listing filtering.

## Three-Round Scorecard

| Round | Segment | Net-New Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Existing Symbols Skipped | Pre-Listing Requests Avoided | Aggregate Symbols |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 292 | shard16 offset10 limit5 | 5 | 636 | 212 | 5 | 0 | 0 | 24 | 349 |
| 293 | shard16 offset16 limit4 | 4 | 528 | 176 | 0 | 0 | 1 | 0 | 353 |
| 294 | shard17 offset0 limit4 | 4 | 447 | 149 | 0 | 0 | 1 | 81 | 357 |
| Total | 3-round block | 13 | 1,611 | 537 | 5 | 0 | 2 | 105 | 357 |

Coverage moved from 344 after Round291 to 357 after Round294: +13 net-new symbols.

Endpoint requests per net-new symbol were about 123.9 across the block. This is still expensive, but the trend improved because Round294 skipped pre-listing periods and avoided known overlap before live requests.

## What Worked

- Startup gates kept this work in CN stock source construction and blocked ETF-rotation confusion.
- Candidate generation stayed blocked until source coverage clears the 1,000-symbol minimum.
- Round292 fixed the combined quality report stale blocker recomputation bug and added regression coverage.
- Round293 split around `000034.SZ` after overlap preview.
- Round294 confirmed shard16 exhaustion before live requests, then split around `000060.SZ`.
- Stock-basic pre-listing filtering remained mandatory and saved 105 endpoint requests across the block.
- Empty requests improved from 5 to 0 to 0.
- Duplicate rows stayed at 0 across all three rounds.
- Required PIT statement column groups passed 2 / 2 in every live round.

## What Did Not Work

- No source root is ready for candidate generation; aggregate source coverage is still only 35.7% of the 1,000-symbol minimum.
- The work produced 0 factor names, 0 IC screens, 0 portfolio grids, and 0 research leads.
- Source construction remains slow relative to the final gate.
- Endpoint cost remains meaningful because each net-new symbol requires full 44-period coverage across three Tushare statement endpoints.

## Direction Audit

The team did not drift back into blind factor mining. The hard gate correctly blocked:

- short-sample IC screens;
- portfolio grids;
- raw Sharpe/rank sorting;
- final-holdout reading;
- paper-ready or live-signal claims.

This is aligned with the requirement to stop wasting time and money on noisy factors. The current work looks like data engineering because it is building the fair testing source before allowing factor discovery.

## Budget And Waste Review

The backfill route should continue only while it keeps adding clean PIT coverage with acceptable endpoint efficiency.

Current three-round evidence:

- accepted preview net-new ratios were 100%, 80%, and 80%;
- no live endpoint spend was used on known existing symbols after preview;
- stock-basic pre-listing filtering saved 105 endpoint requests;
- empty responses fell to 0;
- duplicate rows stayed at 0;
- aggregate coverage advanced by +13 symbols.

The main adjustment is cadence: Round295 must start by reading this review before more live endpoint spend. Operationally it should preview shard17 offset4, split around `000060.SZ`, and only backfill net-new symbols.

## Adjustment For Round295

Continue the route, but do not skip the review gate:

- read this Round292-294 review first;
- run aggregate-overlap preview before every live request batch;
- scan ahead if preview net-new ratio is below 80%;
- split around known existing symbols, especially `000060.SZ` at shard17 offset4;
- use stock-basic pre-listing filtering;
- track empty responses and duplicate rows in every closeout;
- keep candidate generation blocked until 1,000 unique symbols clear the source gate.

Next allowed direction:

```text
round295_start_with_round292_294_three_round_review_then_continue_financial_reporting_timeliness_backfill_on_shard17_offset4_with_overlap_preview_split_around_existing_000060_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```

## Factor Outcome Across Reviewed Rounds

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is not an alpha failure. It is a deliberate decision not to manufacture alpha claims from an under-covered PIT source.
