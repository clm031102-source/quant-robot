# CN Stock Round349 - Shortlist Consistency And Holdout Checklist

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round349 adds a consistency checker for the simulation shortlist and records the pre-holdout checklist.

This round does not run the 2026 holdout.

## New Checker

Module:

`src/quant_robot/ops/simulation_shortlist_check.py`

CLI:

`scripts/check_simulation_shortlist_config.py`

Test:

`tests/unit/test_simulation_shortlist_check.py`

Command run:

`python scripts/check_simulation_shortlist_config.py --config configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json --repo-root .`

Result:

- status: passed;
- blockers: 0;
- candidate count: 3;
- source docs: 8;
- superseded outputs: 2;
- final holdout status: sealed.

## Verification

Commands run:

- `python -m unittest tests.unit.test_simulation_shortlist_check tests.unit.test_trade_capacity_stress`
- `python scripts/check_simulation_shortlist_config.py --config configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json --repo-root .`
- `python -m json.tool configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`

All passed.

## Pre-Holdout Checklist

Do not run 2026 final holdout until all are true:

1. The shortlist config checker passes with zero blockers.
2. The user explicitly starts final validation or simulation-readiness review.
3. The exact candidate IDs are frozen:
   - `primary_high_return`;
   - `primary_defensive_zz500`;
   - `safer_defensive_zz500`.
4. Superseded outputs are not used as evidence.
5. Cost, capacity, and beta audit docs are linked.
6. The run is recorded as read-once holdout usage.
7. No broker, account, order, or live-trading code is invoked.

## Decision

The shortlist package is internally consistent.

Next action under the 10-round rule:

- package and push the Round340-349 work to GitHub;
- then resume mining only if the next work can beat or materially strengthen the packaged shortlist.
