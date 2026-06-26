# CN Stock Low-Vol Reversal Liquidity Incremental Residual Preregistration Round119 - 2026-06-22

## Purpose

Round119 follows the Round118 budget stop-loss:

- soft-capacity low-turnover fixed the capacity problem in the first three OOS folds;
- it still produced 0 accepted rows and 0 positive-relative rows across 108 inspected rows;
- therefore the next useful direction is not another low-turnover sweep.

This round returns to the Round116/117 finding: the Qlib/public low-vol/reversal/liquidity cluster has signal, but the directly observed lead was redundant and exposed to liquidity/market proxies. Round119 pre-registers only incremental residual variants.

## Output

Command:

```powershell
.venv\Scripts\python.exe scripts\run_lowvol_reversal_liquidity_incremental_residual_preregistration.py --output-dir data\reports\lowvol_reversal_liquidity_incremental_residual_preregistration_round119_20260622 --min-candidates 8
```

Result:

- Candidates: 8
- Unique candidate names: 8
- Promotion allowed: 0
- Portfolio backtest allowed: 0
- Next gate: `round120_lowvol_reversal_liquidity_incremental_residual_prescreen`

Reference cluster to neutralize:

- `amount_stability_reversal_5_20`
- `range_contraction_lowvol_reversal_20`
- `pv_lowvol_reversal_blend_20`
- `bollinger_reversal_lowvol_liquid_20`

Exposure controls:

- `log_adv20_amount`
- `beta_120`
- `downside_beta_120`
- `market_corr_60`

## Candidates

| Factor | Family | Purpose |
|---|---|---|
| `qlib_blend_residual_vs_lowvol_cluster_5` | qlib incremental residual | Keep only the Qlib blend residual after known cluster removal |
| `qlib_blend_cluster_exposure_neutral_residual_5` | qlib incremental exposure neutral | Remove cluster plus liquidity/beta/market-correlation exposures |
| `amount_stability_incremental_residual_5_20` | liquidity capacity incremental | Test whether amount stability adds information beyond the cluster |
| `range_contraction_incremental_residual_20` | range incremental residual | Test range contraction after cluster and beta removal |
| `bollinger_reversal_incremental_residual_20` | public technical incremental residual | Test Bollinger reversal after cluster and market-correlation removal |
| `donchian_pullback_incremental_residual_20` | public channel incremental residual | Orthogonalize Donchian pullback against the cluster |
| `rsi_reversal_incremental_residual_14_20` | public oscillator incremental residual | Orthogonalize RSI reversal against cluster/downside beta |
| `pv_lowvol_cluster_residual_spread_20` | price-volume incremental residual | Test residual spread between PV and Bollinger reversal ideas |

## Decision

Round119 is a preregistration round, not empirical alpha evidence.

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research candidates created: 8

Round120 must run an IC/quantile/turnover/exposure prescreen before any portfolio grid:

- incremental IC over the reference cluster;
- residual correlation against known cluster members;
- exposure correlation after neutralization;
- turnover and capacity diagnostics;
- no 2026 final-holdout tuning.
