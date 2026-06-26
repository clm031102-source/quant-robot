# CN Stock Capacity-Safe Trend Accumulation Prescreen Round105

## Command

```powershell
python scripts\run_capacity_safe_trend_accumulation_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\capacity_safe_trend_accumulation_prescreen_round105_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

## Data Window

- Bar assets: 5,707
- Bar rows: 10,785,537
- Bar window: 2015-01-05 to 2025-12-31
- Signal window: 2015-02-02 to 2025-12-31
- Label window: 2015-01-05 to 2025-12-23
- Final 2026 holdout included: false

## Headline Result

- Candidate count: 10
- Factor names with rows: 10
- Factor rows: 100,335,759
- Label rows: 21,417,227
- Aligned rows: 199,187,090
- Tests: 20
- FDR-significant tests: 20
- Research leads: 0
- Promotion allowed candidates: 0

The prescreen completed cleanly, but no Round104 trend/amount accumulation candidate qualifies as a research lead under the project gate. All tests are statistically significant after FDR, yet the registered higher-is-better direction is consistently wrong: mean IC is negative for every factor and horizon, IC>0 rates are only about 24% to 36%, and quantile monotonicity is weak or reversed.

## Top Statistical Rows

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Top-Q turnover | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| accumulation_distribution_proxy_20 | 20 | -0.1005 | -0.681 | -34.93 | 24.0% | 0.0123 | 0.400 | 14.0% | no |
| money_pressure_efficiency_20 | 20 | -0.0952 | -0.709 | -36.36 | 23.6% | -0.0138 | -0.600 | 15.4% | no |
| volume_weighted_momentum_quality_20 | 20 | -0.0928 | -0.689 | -35.33 | 24.0% | -0.0082 | -0.600 | 15.7% | no |
| turnover_expansion_momentum_10_40 | 20 | -0.0899 | -0.639 | -32.76 | 26.0% | 0.0355 | 0.400 | 11.1% | no |
| price_path_efficiency_amount_confirmed_20 | 20 | -0.0803 | -0.590 | -30.27 | 28.2% | 0.0006 | 0.100 | 12.6% | no |
| amount_accumulation_breakout_20_60 | 20 | -0.0787 | -0.618 | -31.68 | 25.8% | 0.0311 | 0.600 | 7.6% | no |
| accumulation_distribution_proxy_20 | 5 | -0.0735 | -0.521 | -26.78 | 28.9% | 0.0180 | 0.900 | 14.0% | no |
| high_volume_breakout_quality_20 | 20 | -0.0458 | -0.388 | -19.92 | 36.0% | 0.0302 | 0.300 | 40.4% | no |

## Audit Judgment

Round105 rejects the positive trend/amount accumulation family as currently registered. This is not a capacity failure: the median signal-date amount and ADV20 are high, and turnover is mostly moderate except for the high-volume breakout candidate. The failure is direction and cross-sectional structure. The public trend/volume intuition "strong trend plus rising amount is better" does not hold in this CN stock long-cycle sample.

The useful evidence is the strong negative IC cluster. It suggests that high trend/amount accumulation may capture overheated, crowded, or late-stage demand rather than durable alpha. That evidence is not enough to promote an inverse factor. Inverting after seeing results would be post-hoc mining unless the inverse direction is pre-registered and tested as a new hypothesis.

## Next Direction

Round106 should pre-register an anti-trend/overheated-amount direction audit before any portfolio grid:

- Test inverse trend/amount accumulation only as a new pre-registered hypothesis.
- Prefer bottom-exclusion or overheated-tail avoidance framing over direct long-only "short the strong trend" framing.
- Keep the same long-cycle IC/quantile/turnover/capacity prescreen before walk-forward or portfolio conversion.
- Reject same-family parameter tuning around the failed positive direction.

Recommended next direction: `round106_negative_ic_trend_accumulation_direction_preregistration`.
