# CN Stock Round733 LPR Macro Regime Reference Dedup Preflight

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round733 routed the four Round732 `gap_widening` residual IC leads into candidate clusters before any factor-value reference deduplication, walk-forward validation, portfolio grid, paper signal, or promotion claim.

This round did not run a portfolio grid, promotion gate, paper simulation, live signal, provider download, broker connection, account read, order placement, or final-holdout tuning.

## Implemented Preflight

New files:

- `src/quant_robot/ops/lpr_macro_regime_reference_dedup_preflight.py`
- `scripts/run_lpr_macro_regime_reference_dedup_preflight.py`
- `tests/unit/test_lpr_macro_regime_reference_dedup_preflight.py`
- `tests/unit/test_lpr_macro_regime_reference_dedup_preflight_cli.py`

The preflight:

- consumes the Round732 pairwise residual IC prescreen and rejects non-ready inputs;
- rebuilds the LPR-SHIBOR gap state from repaired local `external_macro_rates`;
- realigns residual IC observations to the latest LPR state with `available_date <= ic_date`;
- computes pairwise Pearson correlations of residual IC time series inside the lead state;
- clusters lead candidates at absolute IC-curve correlation >= 0.90;
- marks duplicate IC curves at absolute IC-curve correlation >= 0.98;
- selects one representative per cluster by mean IC and ICIR;
- folds in source report reference-correlation and exposure-correlation evidence;
- allows only factor-value reference deduplication for cluster representatives;
- keeps walk-forward, portfolio grids, promotion, and live boundaries blocked.

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
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_reference_dedup_preflight.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --pairwise-prescreen data\reports\round732_lpr_macro_regime_pairwise_residual_ic_prescreen_20260709\lpr_macro_regime_pairwise_residual_ic_prescreen.json --residual-ic data\reports\public_anomaly_residual_ensemble_prescreen_round229_20260624\public_anomaly_residual_ensemble_residual_ic_observations.csv --residual-ic data\reports\public_trend_strength_state_residual_prescreen_round219_20260624\public_trend_strength_state_residual_ic_observations.csv --reference-correlation data\reports\public_anomaly_residual_ensemble_prescreen_round229_20260624\public_anomaly_residual_ensemble_reference_correlations.csv --reference-correlation data\reports\public_trend_strength_state_residual_prescreen_round219_20260624\public_trend_strength_state_reference_correlations.csv --exposure-correlation data\reports\public_anomaly_residual_ensemble_prescreen_round229_20260624\public_anomaly_residual_ensemble_exposure_correlations.csv --exposure-correlation data\reports\public_trend_strength_state_residual_prescreen_round219_20260624\public_trend_strength_state_exposure_correlations.csv --output-dir data\reports\round733_lpr_macro_regime_reference_dedup_preflight_20260709 --cluster-abs-ic-corr 0.90 --duplicate-abs-ic-corr 0.98 --min-pair-overlap 20
```

Output: `data/reports/round733_lpr_macro_regime_reference_dedup_preflight_20260709`

Summary:

- State leads from Round732: 4
- Candidate clusters: 2
- Representative candidates: 2
- Cluster-blocked candidates: 2
- Factor-value reference-dedup candidates allowed next: 2
- Walk-forward preflight allowed candidates: 0
- Portfolio-grid allowed candidates: 0
- Promotion-allowed candidates: 0
- Decision blockers: none
- Next direction: `factor_value_reference_dedup_for_lpr_gap_widening_representatives`

Candidate routing:

| Cluster | Representative | Factor | Mean IC | ICIR | Max IC-corr | Reference | Exposure | Next |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | yes | `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual` | 0.0358 | 0.612 | 1.000 | missing | high exposure | factor-value reference dedup |
| 2 | yes | `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual` | 0.0218 | 0.284 | 0.331 | moderately redundant | high exposure | factor-value reference dedup |
| 1 | no | `public_anomaly_residual_regime_conditioned_20_industry_size_liquidity_vol_residual` | 0.0356 | 0.605 | 1.000 | missing | high exposure | blocked as same cluster |
| 1 | no | `public_anomaly_residual_agreement_20_industry_size_liquidity_vol_residual` | 0.0224 | 0.428 | 0.927 | missing | high exposure | blocked as same cluster |

Pairwise IC-curve checks:

- Equal-weight vs regime-conditioned anomaly: 99 overlapping dates, correlation 1.000, classified as duplicate IC curve.
- Equal-weight vs agreement anomaly: 100 overlapping dates, correlation 0.927, classified as high IC-curve similarity.
- Regime-conditioned vs agreement anomaly: 99 overlapping dates, correlation 0.927, classified as high IC-curve similarity.
- Anomaly representatives vs Williams: correlations 0.140 to 0.331, classified as unique IC curve.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_reference_dedup_preflight.py tests\unit\test_lpr_macro_regime_reference_dedup_preflight_cli.py
```

Result: `3 passed`.

## Decision

Round733 reduces the four Round732 state leads to two representatives for the next factor-value reference-deduplication step:

- `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual`
- `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual`

Do not run walk-forward, portfolio grids, promotion gates, or paper signals yet. Both representatives still require factor-value reference deduplication and exposure reaudit under the `gap_widening` LPR regime before any stronger claim.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
