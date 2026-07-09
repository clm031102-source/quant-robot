# CN Stock Round736 LPR Macro Regime State-Conditioned Walk-Forward Preflight

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round736 froze the Round735 `gap_widening` LPR-SHIBOR representatives for the next formal walk-forward validation step and generated the fold plan.

This round did not run walk-forward return validation, portfolio grids, promotion gates, paper signals, provider downloads, broker connections, account reads, order placement, or final-holdout tuning.

## Implemented Preflight

New files:

- `src/quant_robot/ops/lpr_macro_regime_state_conditioned_walk_forward_preflight.py`
- `scripts/run_lpr_macro_regime_state_conditioned_walk_forward_preflight.py`
- `tests/unit/test_lpr_macro_regime_state_conditioned_walk_forward_preflight.py`
- `tests/unit/test_lpr_macro_regime_state_conditioned_walk_forward_preflight_cli.py`

The preflight:

- consumes the Round735 state-conditioned reference-dedup gate;
- rejects input unless Round735 only allowed the next walk-forward preflight and kept portfolio, promotion, and live boundaries closed;
- rebuilds Round734 residual factor values for the Round735 representatives;
- aligns factor values to the latest LPR state with `available_date <= factor_date`;
- computes candidate-to-candidate factor-value correlations inside `gap_widening`;
- freezes non-duplicate candidates for formal walk-forward validation;
- creates train/test fold definitions by state dates;
- records moderate exposure challenges that must be reported in the later validation;
- keeps portfolio grids, promotion, paper, and live boundaries blocked.

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

## Real Preflight

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_state_conditioned_walk_forward_preflight.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --reference-dedup data\reports\round735_lpr_macro_regime_state_conditioned_reference_dedup_20260709\lpr_macro_regime_state_conditioned_reference_dedup.json --smoke data\reports\round734_lpr_macro_regime_factor_value_reconstruction_smoke_20260709\lpr_macro_regime_factor_value_reconstruction_smoke.json --output-dir data\reports\round736_lpr_macro_regime_state_conditioned_walk_forward_preflight_20260709 --analysis-start-date 2024-07-01 --analysis-end-date 2025-12-31 --lookback-days 60 --min-abs-gap-change 0.01 --min-state-dates 20 --min-median-cross-section 100 --train-state-dates 60 --test-state-dates 20 --step-state-dates 20 --min-walk-forward-folds 2
```

Output: `data/reports/round736_lpr_macro_regime_state_conditioned_walk_forward_preflight_20260709`

Summary:

- Status: `cleared`
- Reference-dedup candidates: 2
- Candidate-pair rows: 1
- Frozen walk-forward candidates: 2
- Cluster duplicates: 0
- Blocked candidates: 0
- Max candidate absolute factor-value correlation: 0.611
- Planned walk-forward folds: 2
- Portfolio-grid allowed candidates: 0
- Promotion-allowed candidates: 0
- Decision blockers: none
- Next direction: `lpr_state_conditioned_walk_forward_cost_capacity_regime_validation`

Candidate freeze table:

| Factor | State | Dates | Median CS | Exposure | Pair corr | Status | Frozen | Challenge |
|---|---|---:|---:|---|---:|---|---|---|
| `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual` | `gap_widening` | 100 | 4,039 | moderate_exposure | 0.611 | frozen | yes | `challenge_realized_vol_20_exposure_in_walk_forward` |
| `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual` | `gap_widening` | 100 | 4,039 | low_exposure | 0.611 | frozen | yes | none |

Candidate-pair evidence:

- Pair: anomaly equal-weight residual vs Williams residual
- State: `gap_widening`
- Pair observations: 100
- Mean Spearman correlation: 0.269
- Mean absolute Spearman correlation: 0.269
- Max absolute Spearman correlation: 0.611
- Median cross-section: 4,039
- Similarity class: `distinct_factor_value`

Walk-forward plan:

| Fold | Train | Test | Purpose |
|---:|---|---|---|
| 1 | 2025-02-20 to 2025-07-28 | 2025-07-29 to 2025-09-01 | preflight plan only, no validation run |
| 2 | 2025-05-30 to 2025-09-01 | 2025-09-02 to 2025-09-29 | preflight plan only, no validation run |

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_state_conditioned_walk_forward_preflight.py tests\unit\test_lpr_macro_regime_state_conditioned_walk_forward_preflight_cli.py
```

Result: `4 passed`.

## Decision

Both `gap_widening` representatives are frozen for the next formal walk-forward cost/capacity/regime validation step.

This is still not alpha, profitability, portfolio, promotion, paper-ready, or live evidence. The next validation must report the anomaly equal-weight candidate's `realized_vol_20` exposure challenge, keep parameter expansion disabled, and keep final holdout sealed until the dedicated final validation gate.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
