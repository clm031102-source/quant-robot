# CN Stock Round282-284 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock financial reporting timeliness source construction
- Review cadence: required every 3 rounds
- Reviewed rounds: 282, 283, 284

## Executive Verdict

This three-round block did not produce profitable factors, and that is the correct outcome. The financial reporting timeliness source is still below the 1,000-symbol minimum, so IC screens, portfolio grids, and promotion claims remain blocked.

The direction was not wrong, but the route is still in source-construction mode rather than factor-discovery mode. It is useful only if it keeps increasing clean point-in-time coverage at a reasonable endpoint cost. The next rounds must keep optimizing for net-new coverage per Tushare request.

## Three-Round Scorecard

| Round | Segment | Net-New Symbols | Endpoint Requests | Processed Rows | Pre-Listing Requests Avoided | Empty Requests | Duplicate Rows | Aggregate Symbols |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 282 | shard13 effective non-overlap positions | 18 | 2,376 | 792 | 0 | 0 | 0 | 302 |
| 283 | shard14 offset0 limit5 | 5 | 594 | 198 | 66 | 0 | 0 | 307 |
| 284 | shard14 offset5 limit5 | 5 | 624 | 208 | 36 | 0 | 0 | 312 |
| Total | 3-round block | 28 | 3,594 | 1,198 | 102 | 0 | 0 | 312 |

Coverage moved from 284 after Round281 to 312 after Round284: +28 net-new symbols.

## What Worked

- Aggregate-overlap preview prevented known duplicate symbols from wasting endpoint requests in Round282.
- Round283 and Round284 previews each found 5 / 5 net-new symbols before live requests.
- Stock-basic pre-listing filtering avoided 102 endpoint requests across Round283-284.
- True post-filter empty requests stayed at 0 for all three rounds.
- Required PIT statement column groups passed 2 / 2 for every live segment.
- The Round283 standard quality-report overwrite bug was fixed and regression-tested.
- Round284 confirmed the standard quality report matched the combined multi-symbol summary.

## What Did Not Work

- No factor generation was allowed because source coverage reached only 312 / 1,000 symbols.
- The route still spends many Tushare requests for small coverage increments.
- Source-ready roots remain 0 because no individual root has broad enough coverage; only the aggregate union is becoming useful.
- The work is productive as data construction, but it is not yet producing tradable signals.

## Direction Audit

The team did not drift back into blind factor mining. The hard gate correctly blocked:

- short-sample IC screens;
- portfolio grids;
- raw Sharpe/rank sorting;
- final-holdout reading;
- paper-ready or live-signal claims.

This is aligned with the user's requirement to avoid wasting time and money on noisy backtests. The cost is that progress is slower and less exciting: we are building the data source before allowing factor discovery.

## Adjustment For Round285

Continue the route, but tighten efficiency:

- run aggregate-overlap preview before every live request batch;
- prefer high net-new segments over contiguous shard blocks when overlap appears;
- keep stock-basic pre-listing filtering mandatory;
- keep checking that standard quality files equal combined ingest summaries;
- continue to block candidate generation until the 1,000-symbol source gate clears;
- if net-new ratio drops materially below 80% for multiple previews, scan ahead across the shard plan before spending live endpoint budget.

Next allowed direction:

```text
round285_continue_financial_reporting_timeliness_backfill_with_stock_basic_prelisting_filter_and_overlap_preview_until_1000_symbols
```

## Factor Outcome Across Reviewed Rounds

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is not a failure of alpha selection; it is an intentional source gate. The route should be judged by source coverage and data quality until the 1,000-symbol threshold clears.
