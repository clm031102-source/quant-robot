# CN Stock Round737 LPR Macro Regime State-Conditioned Walk-Forward Validation

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round737 ran the formal state-conditioned walk-forward validation for the two Round736 frozen `gap_widening` LPR-SHIBOR representatives.

This round did not run a portfolio grid, promotion gate, paper signal, provider download, broker connection, account read, order placement, or final-holdout tuning.

## Implemented Validation

New files:

- `src/quant_robot/ops/lpr_macro_regime_state_conditioned_walk_forward_validation.py`
- `scripts/run_lpr_macro_regime_state_conditioned_walk_forward_validation.py`
- `tests/unit/test_lpr_macro_regime_state_conditioned_walk_forward_validation.py`
- `tests/unit/test_lpr_macro_regime_state_conditioned_walk_forward_validation_cli.py`

The validation:

- consumes the Round736 preflight and rejects input unless the preflight is `cleared`;
- rebuilds Round734 residual factor values for the frozen Round736 candidates;
- rebuilds forward-return labels from local bars with execution lag 1 and horizon 5;
- aligns candidate factor values to the latest LPR state with `available_date <= factor_date`;
- restricts evaluation to each candidate's frozen state, currently `gap_widening`;
- evaluates Round736 train/test folds without parameter expansion;
- computes fold-level train/test IC, cost-adjusted 5-quantile long-short returns, selected-asset counts, capacity participation, and exposure-challenge correlations;
- requires both folds to pass before a candidate can advance to statistical reality check;
- reports LPR allowed and blocked state dates in the validation windows;
- keeps portfolio grids, promotion, paper, final holdout, and live boundaries blocked.

## Startup Gates

Quant PM startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709
```

Result: `status=ready`, `primary_market=CN_ETF`, blockers `[]`.

Factor-mining startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709 --market CN --asset-type stock --commits-allowed --confirm-start
```

Result: `status=cleared`, startup blockers `[]`, pushes disabled.

## Real Validation

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_state_conditioned_walk_forward_validation.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --preflight data\reports\round736_lpr_macro_regime_state_conditioned_walk_forward_preflight_20260709\lpr_macro_regime_state_conditioned_walk_forward_preflight.json --smoke data\reports\round734_lpr_macro_regime_factor_value_reconstruction_smoke_20260709\lpr_macro_regime_factor_value_reconstruction_smoke.json --output-dir data\reports\round737_lpr_macro_regime_state_conditioned_walk_forward_validation_20260709 --analysis-start-date 2024-07-01 --analysis-end-date 2025-12-31 --lookback-days 60 --min-abs-gap-change 0.01 --cost-bps 10 --portfolio-value 1000000 --max-participation-rate 0.01 --min-ic-observations 10 --min-ic-cross-section 30 --min-selected-assets 20 --min-regime-allowed-dates 1 --min-regime-blocked-dates 1 --allow-not-accepted
```

Output: `data/reports/round737_lpr_macro_regime_state_conditioned_walk_forward_validation_20260709`

Summary:

- Status: `rejected`
- Frozen candidates: 2
- Accepted candidates: 0
- Rejected candidates: 2
- Fold results: 4
- Accepted folds: 2
- LPR allowed dates: 160
- LPR blocked dates: 57
- Statistical reality check allowed next: false
- Portfolio grid allowed: false
- Promotion allowed: false
- Decision blocker: `no_accepted_lpr_walk_forward_candidates`
- Next direction: `repair_or_rotate_lpr_state_conditioned_walk_forward_validation`

Candidate results:

| Rank | Factor | Status | Accepted folds | Mean test IC | Mean test net LS | Test net total | Capacity dates | Exposure challenge | Main rejection |
|---:|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual` | rejected | 1/2 | 0.0164 | 0.0003 | 0.0058 | 0 | pass | Fold 1 IC and cost-adjusted long-short failed |
| 2 | `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual` | rejected | 1/2 | 0.0321 | -0.0007 | -0.0143 | 0 | pass | Fold 1 cost-adjusted long-short failed |

Fold details:

| Factor | Fold | Status | Test IC | IC t | IC+ | Test net mean | Test net total | Net+ | Capacity dates | Reasons |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| anomaly equal-weight residual | 1 | rejected | 0.0162 | 1.36 | 60% | -0.0052 | -0.1049 | 25% | 0 | net mean, net total, and net positive rate failed |
| anomaly equal-weight residual | 2 | accepted | 0.0479 | 4.16 | 80% | 0.0038 | 0.0763 | 60% | 0 | none |
| Williams residual | 1 | rejected | -0.0066 | -0.55 | 35% | -0.0031 | -0.0624 | 35% | 0 | IC and net return failed |
| Williams residual | 2 | accepted | 0.0394 | 1.63 | 65% | 0.0037 | 0.0740 | 65% | 0 | none |

Regime coverage:

- Allowed `gap_widening` dates: 160
- Blocked non-`gap_widening` dates: 57
- Fold 1 test window includes 20 `gap_widening` dates and 5 `gap_flat` blocked dates.
- Fold 2 test window includes 20 `gap_widening` dates.

Capacity and exposure:

- Capacity-limited test dates: 0 for both candidates.
- Maximum participation rate stayed near `0.0061%`, below the 1% cap.
- The anomaly equal-weight candidate's `realized_vol_20` exposure challenge passed: mean abs corr 0.274, max abs corr 0.670, both below validation thresholds.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_state_conditioned_walk_forward_validation.py tests\unit\test_lpr_macro_regime_state_conditioned_walk_forward_validation_cli.py
```

Result: `5 passed`.

## Decision

Round737 rejects both LPR `gap_widening` representatives because neither passed both OOS folds after cost-adjusted long-short validation.

Do not proceed to statistical reality check, final holdout, portfolio grid, promotion, paper signal, or live boundary. The next action should repair or rotate the LPR state-conditioned path, using this rejection as negative evidence rather than trying to loosen gates.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
