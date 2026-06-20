# CN Stock Extreme Trade Return Gate - 2026-06-20

## Problem

The 2025 Batch12 OOS review exposed a false-positive pattern: very high Sharpe and total return can be caused by extreme selected trade returns from bad adjusted-price rows. The dedicated Batch12 validator already blocked this case, but the common research path did not surface the same evidence early enough.

## Change

The common CN stock factor workflow now carries an extreme-trade-return gate through four layers:

- Backtest metrics record `max_trade_gross_return`, `max_abs_trade_gross_return`, `p99_abs_trade_gross_return`, and `extreme_trade_return_flag`.
- Experiment leaderboards persist those metrics for each case.
- Walk-forward validation rejects OOS rows with `extreme_oos_trade_return` when `test_extreme_trade_return_flag` is true or `test_max_abs_trade_gross_return > 5.0`.
- Progress audit and promotion gate also block candidates with the same evidence, so partial reports and old accepted rows cannot become promotion candidates.

The active long-cycle configs now explicitly set:

```json
"max_test_abs_trade_gross_return": 5.0
```

## Post-Promotion Hard Gate

The follow-on paper/risk chain now fails closed on promotion status:

- Risk candidate selection only admits candidates whose promotion status is `paper_ready` or `manual_live_review`.
- Daily ops adds `promotion_status_not_paper_ready` as a non-manual blocker when the selected candidate is blocked, research-only, or missing promotion status.
- Risk selected candidates preserve `promotion_status` so downstream artifacts keep promotion-gate provenance instead of becoming bare case IDs.
- The daily-basic low-turnover bucket validation profile now has its own strict promotion gate config and `run_checks.py` promotion-report step, matching the value/size/liquidity and price-volume validation lines.

## Same-Parameter Replay Gate

The long-cycle replay pack now separates coverage/source-metric audit from actual same-parameter full-sample replay:

- `audit_only` means the pack only audited history coverage and upstream source metrics; it is not proof that frozen parameters were rerun across the full long cycle.
- A candidate can reach `validation_candidate` in the long-cycle pack only when explicit replay evidence reports `same_parameter_full_sample_status`, `long_cycle_replay_status`, `full_sample_replay_status`, `performance_replay_status`, or `replay_status` as pass/completed.
- Promotion gate blocks missing or `audit_only` replay status with `long_cycle_replay_status_missing` or `long_cycle_replay_status_audit_only`, even when source metrics, split, cost/capacity, and lookahead audits pass.
- Desktop validation profiles now insert `scripts/run_same_parameter_full_sample_replay.py` between walk-forward progress audit and long-cycle replay. The long-cycle replay step consumes `same_parameter_full_sample_replay.csv`, not the raw walk-forward leaderboard, so source metrics come from an actual frozen-parameter full-sample rerun.

## Current Evidence

The residual moneyflow/regime validation is still incomplete and not promotable:

- Completed folds: 36 / 38
- Robust progress candidates: 0
- Claim blockers: `walk_forward_incomplete`, `requires_formal_promotion_gate`, `no_trade_folds_present`, `regime_filter_all_blocked_no_trade_cases`, `no_robust_progress_candidate`

Current progress audit output:

`data/reports/walk_forward_progress_audit_tushare_moneyflow_residual_regime_current_20260620_after_extreme_gate`

## Verification

Fresh checks run after the workflow change:

```powershell
python -m unittest tests.unit.test_backtest tests.unit.test_walk_forward tests.unit.test_promotion_gate tests.unit.test_walk_forward_progress_audit tests.unit.test_batch12_oos_validation tests.unit.test_check_plan tests.unit.test_desktop_factor_validation tests.unit.test_experiment_grid_cli tests.unit.test_tushare_alpha_factory_cli tests.unit.test_factor_mining_startup_gate
python -m compileall -q src scripts tests
git diff --check
python scripts\run_project_audit.py --json
```

Result: 121 related tests passed, compile passed, project audit passed, and `git diff --check` reported only Windows line-ending warnings.
