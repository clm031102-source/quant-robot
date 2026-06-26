# CN Stock Market Residual Lead Exposure Dedup Round112 - 2026-06-22

## Purpose

Round112 audited the only Round111 research lead, `beta_adjusted_range_contraction_60` at 20-day horizon, before any portfolio grid or promotion claim.

The question was not whether a 30% drawdown is acceptable. The question was whether the signal is distinct, stable, and clean enough to deserve a cost/capacity/walk-forward portfolio bridge.

## Scope

- Machine/task: office_desktop / factor_validation.
- Market/asset: CN stock.
- Data window: 2015-01-05 through 2025-12-31.
- Final holdout: 2026 not included.
- Output pack: `data/reports/market_residual_lead_exposure_dedup_round112_20260622`.
- Stage: exposure, stability, and correlation dedup audit only.

Command:

```powershell
python scripts\run_market_residual_lead_exposure_dedup.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --prescreen-report data\reports\market_residual_risk_premia_prescreen_round111_20260622\market_residual_risk_premia_prescreen.json --output-dir data\reports\market_residual_lead_exposure_dedup_round112_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 20 --execution-lag 1 --sample-every-n-dates 5 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

## Run Summary

- Bar rows: 10,785,537.
- Assets: 5,707.
- Lead factor rows: 9,843,366.
- Reference factor rows: 40,479,172.
- Label rows: 10,665,909.
- IC observations: 2,592.
- Reference factors: 4.
- Highly redundant reference factors: 1.
- High exposure diagnostics: 3.
- Yearly failures: 1.
- Monthly failures: 38 of 129.
- Promotion-allowed candidates: 0.

## Lead IC

| Factor | Horizon | Mean IC | ICIR | t | IC+ | Median Cross Section |
|---|---:|---:|---:|---:|---:|---:|
| `beta_adjusted_range_contraction_60` | 20 | 0.0559 | 0.371 | 18.89 | 67.13% | 3,627 |

This confirms the Round111 signal is real at the IC layer. It does not confirm portfolio profitability or tradability.

## Reference Correlation Dedup

| Reference | Obs | Mean Corr | Mean Abs Corr | Max Abs Corr | Class | Blocker |
|---|---:|---:|---:|---:|---|---|
| `donchian_pullback_lowvol_liquid_20` | 523 | 0.3473 | 0.3665 | 0.9768 | highly redundant | yes |
| `range_contraction_lowvol_reversal_20` | 523 | 0.4881 | 0.4932 | 0.8304 | moderately redundant | yes |
| `bollinger_reversal_lowvol_liquid_20` | 523 | 0.1505 | 0.1876 | 0.5820 | unique | no |
| `pv_lowvol_reversal_blend_20` | 523 | 0.1655 | 0.1790 | 0.5512 | unique | no |

Interpretation: the lead is not just a clone of the entire old price-volume cluster, but it has a hard overlap with the Donchian/range-contraction pullback branch. That blocks direct continuation into a TopN grid.

## Exposure Diagnostics

| Exposure | Obs | Mean Corr | Mean Abs Corr | Max Abs Corr | Class | Blocker |
|---|---:|---:|---:|---:|---|---|
| `residual_vol_60` | 523 | -0.7481 | 0.7589 | 0.9399 | high exposure | yes |
| `market_corr_60` | 523 | 0.5351 | 0.5419 | 0.8595 | high exposure | yes |
| `log_adv20_amount` | 523 | -0.0013 | 0.2112 | 0.9955 | high exposure | yes |
| `beta_120` | 523 | 0.0130 | 0.1753 | 0.7644 | moderate exposure | monitor |
| `downside_beta_120` | 523 | -0.0017 | 0.1496 | 0.7536 | moderate exposure | monitor |

The main return explanation is tightly tied to low residual volatility and market-correlation state. That may still be useful as a risk-premia or risk-control ingredient, but it is not clean enough to promote as standalone alpha.

## Yearly Stability

| Year | IC Obs | Mean IC | IC+ | Failure |
|---:|---:|---:|---:|---|
| 2015 | 185 | -0.1021 | 23.78% | true |
| 2016 | 244 | 0.0112 | 52.87% | false |
| 2017 | 244 | 0.0800 | 75.00% | false |
| 2018 | 243 | 0.0750 | 72.84% | false |
| 2019 | 244 | 0.0715 | 73.77% | false |
| 2020 | 243 | 0.0934 | 75.72% | false |
| 2021 | 243 | 0.0765 | 70.78% | false |
| 2022 | 242 | 0.1057 | 82.23% | false |
| 2023 | 242 | 0.0166 | 61.98% | false |
| 2024 | 241 | 0.1040 | 74.69% | false |
| 2025 | 221 | 0.0447 | 64.25% | false |

2015 is a real regime failure, not a reporting artifact. Monthly diagnostics found 38 failed months out of 129, with the first cluster concentrated in 2015 crash months.

## Gate Decision

Promotion remains blocked.

Blockers:

- `lead_highly_redundant_with_reference_factor`
- `lead_high_exposure_to_market_or_liquidity_proxy`
- `twenty_fifteen_regime_failure_unexplained`
- `yearly_ic_instability`

Drawdown tolerance is not the rejection reason. The blocker is signal cleanliness and robustness: redundancy, strong exposure dependence, and the 2015 failure.

## Conclusion

Round112 produced 0 promotable factors.

The lead is a valid statistical research signal, but not paper-ready and not live/manual usable. It should not go to a TopN portfolio grid now. The next step is the required three-round review of rounds 110-112, then decide whether to:

- rotate family;
- keep the signal only as a risk-control component;
- or preregister a neutralized/orthogonalized version with explicit exposure controls.

Next direction: `round113_round110_112_three_round_review_before_next_action`.
