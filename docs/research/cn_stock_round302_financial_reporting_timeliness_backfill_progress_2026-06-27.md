# CN Stock Round302 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-27
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round302-financial-timeliness-20260627`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round302 continued the financial reporting timeliness source-construction route after the Round299-301 review. It produced no factor names, no IC screens, no portfolio grids, and no promotable candidates. This remains intentional: aggregate financial reporting timeliness coverage is now 394 unique symbols, still below the 1,000-symbol minimum required before candidate generation.

The useful work was:

- started from latest `origin/main` and created a fresh Round302 validation branch;
- cleared the CN stock startup gate for office_desktop / factor_validation;
- read the Round299-301 review before endpoint spend;
- tested the guarded `symbol-limit 6` efficiency probe on shard19;
- rejected two low-efficiency overlap slices before live requests;
- selected shard19 offset12 limit6 only after preview confirmed 6 / 6 net-new symbols;
- backfilled 6 net-new PIT statement symbols;
- increased aggregate source coverage from 388 to 394 unique symbols;
- used stock-basic pre-listing filtering to avoid 183 endpoint requests;
- kept candidate generation blocked because source coverage remains below 1,000 unique symbols.

## Startup Gate

Round302 started from the completed Round301 state.

| Item | Result |
|---|---|
| Machine | office_desktop |
| Task | factor_validation |
| Branch | `codex/factor-validation-cn-stock-round302-financial-timeliness-20260627` |
| CN stock startup gate | cleared |
| Current round state | Round301 completed, Round302 next |
| Candidate generation | blocked until 1,000 unique symbols |

The project remains research-to-review only:

- no broker connection;
- no live account reads;
- no order placement;
- no automatic live trading.

## Pre-Run Inputs Read

Round302 read the required prior artifacts:

```text
docs/research/cn_stock_round299_301_three_round_review_2026-06-27.md
docs/research/cn_stock_round301_financial_reporting_timeliness_backfill_progress_2026-06-27.md
```

The prior decision allowed a guarded `symbol-limit 6` probe only if overlap preview confirmed enough net-new symbols and endpoint budget remained controlled.

## Overlap Preview

Round302 previewed three shard19 slices before live requests.

| Preview | Existing Symbols | Net-New Symbols | Net-New Ratio | Decision |
|---|---:|---:|---:|---|
| shard19 offset0 limit6 | 2 | 4 | 66.7% | reject direct limit6; split later |
| shard19 offset6 limit6 | 2 | 4 | 66.7% | reject direct limit6; split later |
| shard19 offset12 limit6 | 0 | 6 | 100.0% | backfill |

Existing symbols detected in the rejected direct slices:

```text
000415.SZ
000404.SZ
000498.SZ
000156.SZ
```

Net-new symbols backfilled in Round302:

```text
001316.SZ
301322.SZ
002301.SZ
000595.SZ
000978.SZ
002159.SZ
```

## Backfill Result

Round302 backfilled shard19 offset12 limit6 with stock-basic pre-listing filtering enabled.

| Metric | Value |
|---|---:|
| Planned symbol-periods | 264 |
| Active symbol-periods | 203 |
| Pre-listing symbol-periods skipped | 61 |
| Pre-listing endpoint requests avoided | 183 |
| Endpoint count | 3 |
| Endpoint requests | 609 |
| Processed rows | 206 |
| Empty requests | 3 |
| Skipped requests | 0 |
| Duplicate rows | 3 |
| Missing asset id rows | 0 |
| Required column groups passing | 2 / 2 |
| Quality report assets | 6 |
| Quality report rows | 206 |
| Quality report passes | true |

The `limit6` probe was efficient only on the clean offset12 slice. The pre-listing filter reduced live endpoint spend from the planned 792 requests to 609 requests.

## Quality Watch Items

Round302 quality passed, but two watch items must stay visible:

- empty endpoint responses: 3;
- duplicate rows: 3.

The duplicate rows do not block source accumulation for this segment, but they must be removed or isolated before any factor matrix consumes this source.

## Aggregate Source Gate

After Round302, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 112 |
| Aggregate rows | 84,499 |
| Unique symbols | 394 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 388 to 394 unique symbols, but this is still only 39.4% of the 1,000-symbol source gate.

## Factor Outcome

Round302 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is source construction, not alpha discovery. Candidate generation remains blocked until the long-cycle PIT source has enough market coverage.

## Next Direction

Round303 should return to shard19's front overlap slices and backfill only the net-new symbols around the already-previewed existing names. The live run should split around:

```text
000415.SZ
000404.SZ
000498.SZ
000156.SZ
```

Required controls:

- re-run or cite overlap preview before live endpoint spend;
- split around existing symbols;
- keep stock-basic pre-listing filtering enabled;
- track empty responses and duplicate rows;
- keep candidate generation blocked until 1,000 unique symbols pass the source gate.

Next allowed direction:

```text
round303_continue_financial_reporting_timeliness_backfill_on_shard19_front_segments_split_around_existing_000415_000404_000498_000156_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```
