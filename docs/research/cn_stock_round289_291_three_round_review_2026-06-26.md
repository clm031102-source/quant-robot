# CN Stock Round289-291 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock financial reporting timeliness source construction
- Review cadence: required every 3 rounds
- Reviewed rounds: 289, 290, 291
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Verdict

Rounds289-291 correctly produced no factors. The aggregate financial reporting timeliness source reached only 344 / 1,000 unique symbols, so IC screens, portfolio grids, paper-ready claims, and live/manual signals remain blocked.

The direction remains useful as source construction, not yet as alpha discovery. The route is still improving clean point-in-time statement coverage, and the endpoint discipline improved: Round289 scanned ahead after a weak preview, Round290 detected a shard tail before live requests, and Round291 selected a 100% net-new block.

## Three-Round Scorecard

| Round | Segment | Net-New Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Existing Symbols Skipped | Aggregate Symbols |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 289 | shard15 offset15/19 net-new subsegments | 4 | 528 | 180 | 27 | 4 | 1 | 335 |
| 290 | shard16 offset0/2 net-new subsegments | 4 | 528 | 176 | 8 | 0 | 1 | 339 |
| 291 | shard16 offset5 limit5 | 5 | 660 | 220 | 5 | 0 | 0 | 344 |
| Total | 3-round block | 13 | 1,716 | 576 | 40 | 4 | 2 | 344 |

Coverage moved from 331 after Round288 to 344 after Round291: +13 net-new symbols.

Endpoint requests per net-new symbol were about 132.0 across the block. This is not cheap, but it is acceptable for full 44-period, 3-endpoint statement coverage while the source remains below gate.

## What Worked

- Quant PM startup gate confirmed the CN stock work did not overwrite the ETF primary research direction.
- CN stock startup gates kept the scope on A-share stocks and blocked ETF-rotation confusion.
- Aggregate-overlap preview ran before every live endpoint segment.
- Round289 rejected shard15 offset10 because it was only 60% net-new, then scanned ahead before live spend.
- Round290 detected shard15 exhaustion before live spend and moved to shard16.
- Round291 found a 5 / 5 net-new block.
- Round289 and Round290 split around already-covered symbols before live requests.
- Stock-basic pre-listing filtering remained mandatory.
- Required PIT statement column groups passed 2 / 2 for all three live rounds.
- Duplicate rows fell from 4 in Round289 to 0 in Rounds290-291.
- Empty requests improved from 27 to 8 to 5.

## What Did Not Work

- No source root is ready for candidate generation; aggregate source coverage is still only 34.4% of the 1,000-symbol minimum.
- The work produced 0 factor names, 0 IC screens, 0 portfolio grids, and 0 research leads.
- Round291 exposed a workflow timeout problem: five-symbol full-period statement segments can exceed a 10-minute shell timeout when the external API is slow.
- Source construction remains slow relative to the final gate.

## Direction Audit

The team did not drift back into blind factor mining. The hard gate correctly blocked:

- short-sample IC screens;
- portfolio grids;
- raw Sharpe/rank sorting;
- final-holdout reading;
- paper-ready or live-signal claims.

This is aligned with the requirement to stop wasting time and money on noisy factors. The cost is that the current work looks like data engineering: it is building the fair testing source before allowing factor discovery.

## Budget And Waste Review

The backfill route should continue only while it keeps adding clean PIT coverage with acceptable endpoint efficiency.

Current three-round evidence:

- net-new ratio remained acceptable after preview: 80%, 80%, 100% for the accepted live blocks;
- endpoint cost per new symbol was high but explainable by full statement coverage;
- empty responses are non-zero but improving;
- duplicate rows are back to zero;
- no live endpoint spend was used on known existing symbols after preview.

The main adjustment is operational: Round292 should increase the wrapper timeout or split full five-symbol batches when API latency is high. It should not terminate a live segment merely because the shell wrapper timeout is shorter than the external API completion time.

## Adjustment For Round292

Continue the route, but tighten the pre-run and timeout standard:

- run aggregate-overlap preview before every live request batch;
- scan ahead if preview net-new ratio is below 80%;
- split around known existing symbols;
- use stock-basic pre-listing filtering;
- set a longer timeout for five-symbol full-period statement batches, or split into smaller subsegments;
- track empty responses and duplicate rows in every closeout;
- keep candidate generation blocked until 1,000 unique symbols clear the source gate.

Next allowed direction:

```text
round292_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_overlap_preview_timeout_budget_and_empty_response_watch_until_1000_symbols_after_round289_291_review
```

## Factor Outcome Across Reviewed Rounds

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is not yet an alpha failure. It is a deliberate decision not to manufacture alpha claims from an under-covered PIT source.
