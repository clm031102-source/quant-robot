# CN Stock Round300 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-27
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round300-financial-timeliness-20260627`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round300 continued the financial reporting timeliness source-construction route after the Round290-299 ten-round package. It produced no factor names, no IC screens, no portfolio grids, and no promotable candidates. This remains intentional: aggregate financial reporting timeliness coverage is now 384 unique symbols, still below the 1,000-symbol minimum required before candidate generation.

The useful work was:

- started from latest `main` and created a fresh Round300 validation branch;
- cleared the CN stock startup gate for office_desktop / factor_validation;
- read the Round299 closeout and Round290-299 ten-round package before endpoint spend;
- previewed shard18 offset10 limit5 before live requests;
- confirmed all five selected symbols were net-new;
- backfilled 5 net-new PIT statement symbols;
- increased aggregate source coverage from 379 to 384 unique symbols;
- kept duplicate rows at 0 and required financial column groups at 2 / 2;
- kept candidate generation blocked because source coverage remains below 1,000 unique symbols.

## Startup Gate

Round300 started from the completed Round299 state.

| Item | Result |
|---|---|
| Machine | office_desktop |
| Task | factor_validation |
| Branch | `codex/factor-validation-cn-stock-round300-financial-timeliness-20260627` |
| CN stock startup gate | cleared |
| Current round state | Round299 completed, Round300 next |
| Candidate generation | blocked until 1,000 unique symbols |

The project remains research-to-review only:

- no broker connection;
- no live account reads;
- no order placement;
- no automatic live trading.

## Pre-Run Inputs Read

Round300 read the required prior artifacts:

```text
docs/research/cn_stock_round299_financial_reporting_timeliness_backfill_progress_2026-06-26.md
docs/research/cn_stock_round290_299_ten_round_result_package_2026-06-26.md
```

The prior decision required continuing shard18 source construction with overlap preview, stock-basic pre-listing filtering, quality-report recomputation, and no candidate generation before the 1,000-symbol source gate.

## Overlap Preview

Round300 previewed shard18 offset10 limit5.

| Metric | Value |
|---|---:|
| Shard id | 18 |
| Symbol offset | 10 |
| Symbol limit | 5 |
| Financial roots scanned | 108 |
| Existing symbols | 0 |
| Net-new symbols | 5 |
| Net-new ratio | 100% |

Net-new symbols:

```text
000739.SZ
000683.SZ
002353.SZ
000782.SZ
000517.SZ
```

Because all five selected symbols were net-new, the live backfill was allowed without splitting.

## Backfill Result

Round300 backfilled the five net-new symbols with stock-basic pre-listing filtering enabled.

| Metric | Value |
|---|---:|
| Planned symbol-periods | 220 |
| Active symbol-periods | 220 |
| Pre-listing symbol-periods skipped | 0 |
| Pre-listing endpoint requests avoided | 0 |
| Endpoint count | 3 |
| Endpoint requests | 660 |
| Processed rows | 220 |
| Empty requests | 2 |
| Skipped requests | 0 |
| Duplicate rows | 0 |
| Missing asset id rows | 0 |
| Required column groups passing | 2 / 2 |
| Quality report assets | 5 |
| Quality report rows | 220 |
| Quality report passes | true |

Backfilled symbols:

```text
000739.SZ
000683.SZ
002353.SZ
000782.SZ
000517.SZ
```

The two empty endpoint responses are flagged as a source-quality watch item. They do not block this segment because the final processed PIT input still passes both required column groups.

## Aggregate Source Gate

After Round300, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 109 |
| Aggregate rows | 82,584 |
| Unique symbols | 384 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 379 to 384 unique symbols, but this is still only 38.4% of the 1,000-symbol source gate.

## Factor Outcome

Round300 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is not an alpha failure. It is a deliberate refusal to test or promote financial reporting timeliness factors from an under-covered source.

## Next Direction

Round301 should continue source construction from shard18 offset15, then trigger the required Round299-301 three-round review after completion.

Required controls:

- run overlap preview before live endpoint spend;
- scan ahead if net-new ratio is below 80%;
- split around existing symbols if preview finds overlap;
- keep stock-basic pre-listing filtering enabled;
- track empty responses and duplicate rows;
- keep candidate generation blocked until 1,000 unique symbols pass the source gate.

Next allowed direction:

```text
round301_continue_financial_reporting_timeliness_backfill_on_shard18_offset15_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_then_round299_301_review_until_1000_symbols
```
