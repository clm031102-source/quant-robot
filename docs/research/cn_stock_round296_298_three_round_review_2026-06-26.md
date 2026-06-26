# CN Stock Round296-298 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock financial reporting timeliness source construction
- Review cadence: required every 3 rounds
- Reviewed rounds: 296, 297, 298
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Verdict

Rounds296-298 correctly produced no factors. The aggregate financial reporting timeliness source reached only 372 / 1,000 unique symbols, so IC screens, portfolio grids, paper-ready claims, and live/manual signals remain blocked.

The direction remains useful as source construction, not alpha discovery yet. The route finished shard17, improved coverage by +11 symbols, kept required financial column groups healthy, and added a reusable fix for the source-audit memory risk.

## Three-Round Scorecard

| Round | Segment | Net-New Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Pre-Listing Requests Avoided | Aggregate Symbols |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 296 | shard17 offset9 limit5 | 5 | 660 | 220 | 2 | 0 | 0 | 366 |
| 297 | shard17 offset14 limit5 | 5 | 660 | 220 | 5 | 0 | 0 | 371 |
| 298 | shard17 offset19 limit5 | 1 | 132 | 44 | 0 | 0 | 0 | 372 |
| Total | 3-round block | 11 | 1,452 | 484 | 7 | 0 | 0 | 372 |

Coverage moved from 361 after Round295 to 372 after Round298: +11 net-new symbols.

Endpoint requests per net-new symbol were exactly 132 across the block. That is expected for a fully listed symbol across 44 statement periods and three Tushare endpoints.

## What Worked

- Startup gates kept this work in CN stock source construction and blocked ETF-rotation confusion.
- Candidate generation stayed blocked until source coverage clears the 1,000-symbol minimum.
- Round296 recovered cleanly from a live API command timeout by rerunning the same output directory with resume behavior.
- Round297 maintained clean duplicate control and required financial column coverage.
- Round298 completed shard17 with the final remaining net-new symbol.
- Duplicate rows stayed at 0 across the whole block.
- Required PIT statement column groups passed 2 / 2 in every live round.
- The aggregate audit memory failure was traced to incorrect root scope and fixed in reusable code.

## What Did Not Work

- No source root is ready for candidate generation; aggregate source coverage is still only 37.2% of the 1,000-symbol minimum.
- The block produced 0 factor names, 0 IC screens, 0 portfolio grids, and 0 research leads.
- Source construction is still slow relative to the final gate.
- The last shard17 slice had only one remaining symbol, so the round delivered limited incremental coverage.
- Round296 and Round297 still had 7 combined empty endpoint responses, which should remain a watch item before factor-matrix construction.

## Direction Audit

The work did not drift back into blind factor mining. The hard gate correctly blocked:

- short-sample IC screens;
- portfolio grids;
- raw Sharpe/rank sorting;
- final-holdout reading;
- paper-ready or live-signal claims.

This is aligned with the requirement to stop wasting time and money on noisy factors. The current work looks like data engineering because it is building the fair testing source before allowing factor discovery.

## Budget And Waste Review

The backfill route should continue only while it keeps adding clean PIT coverage with acceptable endpoint efficiency.

Current three-round evidence:

- accepted preview net-new ratios were 100%, 100%, and 100%;
- no live endpoint spend was used on known existing symbols after preview;
- post-filter empty requests fell to 0 in Round298;
- duplicate rows stayed at 0;
- aggregate coverage advanced by +11 symbols;
- the broad-root audit failure created a reusable code fix and regression test, so the same mistake should not recur.

The main adjustment is cadence: Round299 must start by reading this review before more live endpoint spend. Operationally it should preview shard18 offset0, split around any existing symbols found by preview, and only backfill net-new symbols.

## Adjustment For Round299

Continue the route, but do not skip the review gate:

- read this Round296-298 review first;
- run aggregate-overlap preview before every live request batch;
- scan ahead if preview net-new ratio is below 80%;
- split around known existing symbols;
- use stock-basic pre-listing filtering;
- track empty responses and duplicate rows in every closeout;
- keep candidate generation blocked until 1,000 unique symbols clear the source gate.

Next allowed direction:

```text
round299_start_with_round296_298_three_round_review_then_continue_financial_reporting_timeliness_backfill_on_shard18_offset0_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
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
