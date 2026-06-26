# CN Stock Round248 Startup Method Protocol Optimization

Date: 2026-06-25
Machine: office_desktop
Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
Task: factor_validation

## Scope

This round updates the reusable CN stock factor-mining startup gate before resuming alpha discovery.

It is a process-control change only. It makes no Sharpe, annual-return, profit-rate, win-rate, drawdown, paper-ready, or live-trading claim.

## Problem Fixed

The previous startup gate already contained the eight method-control areas requested by the user:

- A-share real tradeability constraints.
- Point-in-time financial availability.
- Industry/style neutralization.
- CN ETF signal boundary.
- Portfolio construction and metric pack.
- Strict statistical reality checks.
- China market-regime context.
- Event-factor controls.

The weak point was state drift: the default startup config still pointed to the older Round236 accounting-statement backfill direction, even though Rounds 245-247 had already rejected simple realized accounting-statement mutations and required a family rotation.

## Changes

- Added `round_state` to startup gate packets.
- The state records:
  - last completed round: 247;
  - next round: 248;
  - latest three-round review: `docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md`;
  - decision: `rotate_family`;
  - next direction: `round248_rotate_to_external_revision_or_nonfinancial_event_context`;
  - blocked reentry families for simple realized statement formula mutations.
- Added startup validation that rejects stale or inconsistent state:
  - missing `round_state`;
  - `next_round != last_completed_round + 1`;
  - unsupported three-round review decision;
  - `round_state.next_direction` different from `repeatable_mining_protocol.next_direction`;
  - method contract next direction different from the repeatable protocol.
- Updated default config and per-run confirmations so future startup reports surface the Round245-247 audit and Round248 rotation.
- Added Markdown rendering for the current round state.

## Round248 Direction

The next mining round must not mutate the same realized statement formula family again.

Allowed next direction:

`round248_rotate_to_external_revision_or_nonfinancial_event_context`

Required before factor generation:

- Pre-register an external revision or nonfinancial event family.
- Use PIT available dates or event dates.
- Run the 2015-2025 long-cycle residual IC prescreen.
- Require FDR, neutral gates, and quantile shape before any portfolio grid.
- Keep final holdout unread.

## Verification

Commands run:

```powershell
.venv\Scripts\python.exe -m json.tool configs\factor_mining_startup_cn_stock.json > $null
.venv\Scripts\python.exe -m unittest tests.unit.test_factor_mining_startup_gate tests.unit.test_factor_mining_startup_gate_cli
.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\round248_startup_method_protocol_20260625 > $null
```

Validation result:

```text
cleared
round248_rotate_to_external_revision_or_nonfinancial_event_context
round248_rotate_to_external_revision_or_nonfinancial_event_context
```

No broker connection, account read, order placement, automatic live trading, or final-holdout tuning was opened.
