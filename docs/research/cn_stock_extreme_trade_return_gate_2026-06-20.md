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
