# CN Stock Round732 LPR Macro Regime Pairwise Residual IC Prescreen

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round732 paired the Round731 LPR-SHIBOR gap regime state with existing residual stock-factor IC observations.

This round did not create a standalone LPR stock rank, run a portfolio grid, run a promotion gate, create a paper signal, connect to a broker, read an account, place an order, or tune on the final holdout.

The goal was only to test whether already residualized CN stock factor IC observations show a state-conditional research lead under the LPR macro regime.

## Implemented Prescreen

New files:

- `src/quant_robot/ops/lpr_macro_regime_pairwise_residual_ic_prescreen.py`
- `scripts/run_lpr_macro_regime_pairwise_residual_ic_prescreen.py`
- `tests/unit/test_lpr_macro_regime_pairwise_residual_ic_prescreen.py`
- `tests/unit/test_lpr_macro_regime_pairwise_residual_ic_prescreen_cli.py`

The prescreen:

- consumes the Round731 LPR state prescreen output and rejects non-ready state inputs;
- rebuilds the LPR-SHIBOR gap state from repaired local `external_macro_rates`;
- loads one or more residual IC observation CSV files;
- aligns each IC date to the latest LPR state with `available_date <= ic_date`;
- audits unpaired rows and future-date violations separately;
- computes residual IC by `source_id`, factor, horizon, and LPR state;
- applies Bonferroni and Benjamini-Hochberg FDR accounting across state tests;
- allows only the next reference-dedup and walk-forward preflight when state leads exist;
- keeps portfolio grids, promotion, and live boundaries blocked.

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

## Real Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_pairwise_residual_ic_prescreen.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --state-prescreen data\reports\round731_lpr_macro_regime_state_prescreen_20260709\lpr_macro_regime_state_prescreen.json --residual-ic data\reports\public_anomaly_residual_ensemble_prescreen_round229_20260624\public_anomaly_residual_ensemble_residual_ic_observations.csv --residual-ic data\reports\public_trend_strength_state_residual_prescreen_round219_20260624\public_trend_strength_state_residual_ic_observations.csv --output-dir data\reports\round732_lpr_macro_regime_pairwise_residual_ic_prescreen_20260709 --analysis-start-date 2024-07-01 --analysis-end-date 2025-12-31 --lookback-days 60 --min-abs-gap-change 0.01 --min-state-ic-observations 20 --min-mean-ic 0.02 --min-icir 0.20 --min-positive-ic-rate 0.55
```

Output: `data/reports/round732_lpr_macro_regime_pairwise_residual_ic_prescreen_20260709`

Inputs:

- `public_anomaly_residual_ensemble_prescreen_round229_20260624`
- `public_trend_strength_state_residual_prescreen_round219_20260624`

Summary:

- Residual IC files: 2
- Residual IC rows loaded: 25,651
- Analysis-window IC rows: 3,535
- IC rows paired to an LPR state: 3,526
- Residual factors: 10
- State tests: 40
- State research leads: 4
- Candidate research leads: 4
- Decision blockers: none
- Portfolio-grid allowed candidates: 0
- Promotion-allowed candidates: 0
- Next direction: `lpr_regime_state_reference_dedup_walk_forward_preflight`

Pairing audit:

- State join misses: 9
- Available-date-after-IC-date violations: 0
- Paired states: 4
- Directional states: 2

State leads:

| Source | Factor | State | Obs | Mean IC | ICIR | t-stat | Positive IC |
|---|---|---|---:|---:|---:|---:|---:|
| `public_anomaly_residual_ensemble_prescreen_round229_20260624` | `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual` | `gap_widening` | 100 | 0.0358 | 0.612 | 6.12 | 71.0% |
| `public_anomaly_residual_ensemble_prescreen_round229_20260624` | `public_anomaly_residual_regime_conditioned_20_industry_size_liquidity_vol_residual` | `gap_widening` | 99 | 0.0356 | 0.605 | 6.02 | 70.7% |
| `public_anomaly_residual_ensemble_prescreen_round229_20260624` | `public_anomaly_residual_agreement_20_industry_size_liquidity_vol_residual` | `gap_widening` | 100 | 0.0224 | 0.428 | 4.28 | 73.0% |
| `public_trend_strength_state_residual_prescreen_round219_20260624` | `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual` | `gap_widening` | 100 | 0.0218 | 0.284 | 2.84 | 57.0% |

All four state leads are in `gap_widening`. Non-directional states and below-threshold directional states remain diagnostic only.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_pairwise_residual_ic_prescreen.py tests\unit\test_lpr_macro_regime_pairwise_residual_ic_prescreen_cli.py
```

Result: `5 passed`.

## Decision

Round732 upgrades `lpr_shibor_credit_gap_regime_60` from state-ready to residual-IC-pairing-ready for the four listed `gap_widening` leads.

This is still not portfolio, promotion, paper-ready, or live evidence. The only allowed next step is reference deduplication and walk-forward preflight for the four state-conditional residual candidates, with cost/capacity, regime coverage, multiple-testing, final-holdout, and paper-lane gates still required.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
