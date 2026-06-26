# CN Stock Market Residual Risk Premia Prescreen Round111

## Scope

- Machine/task: office_desktop / factor_validation.
- Market/asset: CN stock.
- Data window: 2015-01-05 through 2025-12-31.
- Final holdout: 2026 data not included.
- Output pack: `data/reports/market_residual_risk_premia_prescreen_round111_20260622`.
- Stage: Alphalens-style IC, quantile, FDR, and turnover prescreen only.

## Method

Round111 replayed the 10 Round110 pre-registered market-residual risk-premia candidates without parameter tuning. It built a same-date equal-weight CN stock market proxy, calculated rolling beta/residual features using signal-date information only, and evaluated 5-day and 20-day forward-return labels with execution lag 1.

Hard limits kept in force:

- No top-N portfolio grid.
- No promotion from prescreen alone.
- No full-period normalization.
- No final holdout read.
- No inverse direction promotion without a new preregistration.

## Run Summary

- Bar rows: 10,785,537.
- Bar assets: 5,707.
- Factor rows: 98,318,149.
- Label rows: 21,417,227.
- Aligned rows: 195,158,252.
- Candidate count: 10.
- Factor x horizon tests: 20.
- FDR-significant tests: 20.
- Research leads: 1.
- Promotion-allowed candidates: 0.
- Next direction: `round112_market_residual_lead_exposure_dedup`.

## Lead

Only one candidate passed the strict research-lead gate:

| Factor | Horizon | IC | ICIR | t | IC+ | Q5-Q1 | Monotonicity | Top-Q Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `beta_adjusted_range_contraction_60` | 20 | 0.0559 | 0.371 | 18.89 | 67.1% | 0.1273 | 1.000 | 6.3% |

This is a better result than the previous zero-lead families because it has positive IC, positive quantile spread, perfect quintile monotonicity, and low top-quantile turnover. It is still not promotable because it has not passed market exposure diagnostics, correlation dedup, cost/capacity portfolio replay, regime review, or walk-forward validation.

## Stability Warning

The 20-day lead is not uniformly positive across all years:

| Year | IC Observations | Mean IC | Positive IC Rate |
|---:|---:|---:|---:|
| 2015 | 185 | -0.1021 | 23.8% |
| 2016 | 244 | 0.0112 | 52.9% |
| 2017 | 244 | 0.0800 | 75.0% |
| 2018 | 243 | 0.0750 | 72.8% |
| 2019 | 244 | 0.0715 | 73.8% |
| 2020 | 243 | 0.0934 | 75.7% |
| 2021 | 243 | 0.0765 | 70.8% |
| 2022 | 242 | 0.1057 | 82.2% |
| 2023 | 242 | 0.0166 | 62.0% |
| 2024 | 241 | 0.1040 | 74.7% |
| 2025 | 221 | 0.0447 | 64.3% |

The 2015 failure is material. Round112 must identify whether this is a regime exposure, crash-period weakness, data issue, listing/universe artifact, or a genuine state dependency. This lead cannot move to a top-N portfolio grid before that audit.

## Other Notable Signals

The following positive-IC candidates were statistically significant but failed the research-lead gate, usually because ICIR was below threshold:

| Factor | Horizon | IC | ICIR | IC+ | Q5-Q1 | Monotonicity |
|---|---:|---:|---:|---:|---:|---:|
| `idio_vol_low_60` | 20 | 0.0408 | 0.246 | 61.3% | 0.0979 | 0.900 |
| `beta_adjusted_range_contraction_60` | 5 | 0.0403 | 0.280 | 63.3% | 0.0434 | 0.900 |
| `residual_reversal_5_60` | 5 | 0.0312 | 0.253 | 61.4% | 0.0111 | 0.700 |
| `residual_reversal_5_60` | 20 | 0.0297 | 0.249 | 60.5% | 0.0241 | 0.700 |

The strongly negative-IC rows, including `residual_momentum_quality_20_120` and `low_market_corr_60`, are not promotion evidence. Any inverse-direction use requires a fresh preregistration and separate audit.

## Decision

Proceed to Round112 with a narrow lead audit:

1. Audit `beta_adjusted_range_contraction_60` 20-day exposure to market beta, raw volatility, size/liquidity, and industry concentration.
2. Explain or reject the 2015 failure.
3. Deduplicate against existing price-volume/range-contraction clusters before any portfolio grid.
4. Keep top-N promotion blocked until exposure, correlation, cost/capacity, regime, and walk-forward gates clear.

