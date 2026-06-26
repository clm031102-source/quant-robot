# CN Stock Round301 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-27
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round301-financial-timeliness-20260627`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Executive Summary

Round301 continued the financial reporting timeliness source-construction route and completed the required shard18 tail pass. It produced no factor names, no IC screens, no portfolio grids, and no promotable candidates. This remains intentional: aggregate financial reporting timeliness coverage is now 388 unique symbols, still below the 1,000-symbol minimum required before candidate generation.

The useful work was:

- started from latest `origin/main` and created a fresh Round301 validation branch;
- cleared the CN stock startup gate for office_desktop / factor_validation;
- read the Round300 closeout and Round290-299 ten-round package before endpoint spend;
- previewed shard18 offset15 limit5 before live requests;
- detected one already-covered symbol and split around it before endpoint spend;
- backfilled 4 net-new PIT statement symbols;
- increased aggregate source coverage from 384 to 388 unique symbols;
- kept duplicate rows at 0 and required financial column groups at 2 / 2 in both subsegments;
- kept candidate generation blocked because source coverage remains below 1,000 unique symbols.

## Startup Gate

Round301 started from the completed Round300 state.

| Item | Result |
|---|---|
| Machine | office_desktop |
| Task | factor_validation |
| Branch | `codex/factor-validation-cn-stock-round301-financial-timeliness-20260627` |
| CN stock startup gate | cleared |
| Current round state | Round300 completed, Round301 next |
| Candidate generation | blocked until 1,000 unique symbols |

The project remains research-to-review only:

- no broker connection;
- no live account reads;
- no order placement;
- no automatic live trading.

## Pre-Run Inputs Read

Round301 read the required prior artifacts:

```text
docs/research/cn_stock_round300_financial_reporting_timeliness_backfill_progress_2026-06-27.md
docs/research/cn_stock_round290_299_ten_round_result_package_2026-06-26.md
```

The prior decision required continuing shard18 source construction with overlap preview, stock-basic pre-listing filtering, quality-report recomputation, and no candidate generation before the 1,000-symbol source gate. It also required a Round299-301 three-round review after Round301 completion.

## Overlap Preview

Round301 previewed shard18 offset15 limit5.

| Metric | Value |
|---|---:|
| Shard id | 18 |
| Symbol offset | 15 |
| Symbol limit | 5 |
| Financial roots scanned | 109 |
| Existing symbols | 1 |
| Net-new symbols | 4 |
| Net-new ratio | 80% |

Existing symbol skipped before live requests:

```text
000078.SZ
```

Net-new symbols:

```text
000710.SZ
002156.SZ
600415.SH
002072.SZ
```

Because the existing symbol sat at offset16, Round301 split the live requests into offset15 limit1 and offset17 limit3.

## Backfill Result

Round301 backfilled the four net-new symbols with stock-basic pre-listing filtering enabled.

| Segment | Symbols | Active Symbol-Periods | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Required Groups | Passes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| shard18 offset15 limit1 | 1 | 44 | 132 | 44 | 2 | 0 | 2 / 2 | true |
| shard18 offset17 limit3 | 3 | 132 | 396 | 132 | 0 | 0 | 2 / 2 | true |
| total | 4 | 176 | 528 | 176 | 2 | 0 | 2 / 2 | true |

Backfilled symbols:

```text
000710.SZ
002156.SZ
600415.SH
002072.SZ
```

The two empty endpoint responses are flagged as a source-quality watch item. They do not block this segment because the final processed PIT input still passes both required column groups.

## Quality Report

| Metric | offset15 limit1 | offset17 limit3 | Total |
|---|---:|---:|---:|
| Assets | 1 | 3 | 4 |
| Rows | 44 | 132 | 176 |
| Duplicate rows | 0 | 0 | 0 |
| Missing asset id rows | 0 | 0 | 0 |
| Required column groups passing | 2 / 2 | 2 / 2 | 2 / 2 |
| Ann date start | 2015-04-25 | 2015-04-28 | 2015-04-25 |
| Ann date end | 2026-04-29 | 2026-04-17 | 2026-04-29 |
| Report period start | 2015-03-31 | 2015-03-31 | 2015-03-31 |
| Report period end | 2025-12-31 | 2025-12-31 | 2025-12-31 |

## Aggregate Source Gate

After Round301, the aggregate financial reporting timeliness source audit reported:

| Metric | Value |
|---|---:|
| Aggregate sources | 111 |
| Aggregate rows | 83,468 |
| Unique symbols | 388 |
| Minimum required unique symbols | 1,000 |
| Source-ready roots | 0 |
| Candidate plan allowed | false |

Gate blocker:

```text
unique_symbol_count_below_minimum
```

Coverage improved from 384 to 388 unique symbols, but this is still only 38.8% of the 1,000-symbol source gate.

## Factor Outcome

Round301 produced:

- new factor names: 0
- IC screens: 0
- portfolio grids: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is not an alpha failure. It is a deliberate refusal to test or promote financial reporting timeliness factors from an under-covered source.

## Next Direction

Round301 completes shard18. Round302 should start shard19 offset0. To improve throughput without weakening controls, Round302 may use a guarded `symbol-limit 6` efficiency probe only if overlap preview confirms enough net-new symbols and endpoint budget remains controlled. If preview finds overlap, split around existing symbols as before.

Required controls:

- run overlap preview before live endpoint spend;
- scan ahead if net-new ratio is below 80%;
- split around existing symbols if preview finds overlap;
- keep stock-basic pre-listing filtering enabled;
- track empty responses and duplicate rows;
- keep candidate generation blocked until 1,000 unique symbols pass the source gate.

Next allowed direction:

```text
round302_continue_financial_reporting_timeliness_backfill_on_shard19_offset0_limit6_efficiency_probe_with_overlap_preview_stock_basic_prelisting_filter_quality_report_recompute_guard_until_1000_symbols
```
