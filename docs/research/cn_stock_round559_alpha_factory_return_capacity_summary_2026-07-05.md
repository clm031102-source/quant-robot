# CN Stock Round559 Alpha-Factory Return Capacity Summary

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: make alpha-factory summaries report portfolio return quality and capacity blocker counts directly, so future gated source-readiness runs do not require manual leaderboard inspection before deciding whether IC evidence is useful.

## Change

`src\quant_robot\research\alpha_factory.py` now adds these summary fields:

| Field | Meaning |
| --- | --- |
| `capacity_limited` | Number of rows with `capacity_limited_trades > 0` |
| `positive_total_return` | Number of rows with `total_return > 0` |
| `positive_sharpe` | Number of rows with `sharpe > 0` |
| `paper_eligible_positive_return` | Internal paper-eligible rows with positive total return |
| `paper_eligible_negative_return` | Internal paper-eligible rows with negative total return |

The existing IC and multiple-testing summary fields remain unchanged.

## Test Evidence

- Added `test_summary_counts_capacity_and_return_quality`.
- Focused red test first failed with missing `capacity_limited` in `_summary`.
- After implementation, focused test passed.
- Related alpha-factory and CLI unit coverage passed with 21 tests.
- Python compile passed for `src\quant_robot\research\alpha_factory.py` and `scripts\run_tushare_alpha_factory.py`.

## Research Use

This is a reporting improvement, not a new alpha result. It makes the Round558 problem visible in future manifests: IC-pass rows can still be poor if they have negative realized return, negative Sharpe, or capacity-limited trades.

Future longer discovery-window diagnostics should use these fields in their lightweight Markdown summaries before any walk-forward replay or paper-simulation packaging.

## Decision

Do not promote any daily-basic candidate from Round559. Use the new summary fields as required diagnostics for the next longer source-readiness run.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download.
- No final-holdout tuning.
- Generated `data/reports` artifacts remain out of Git.
