# CN Stock Round268 Forecast/Express Disagreement PIT Prescreen

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock cross-sectional alpha research
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## What Changed

Round268 implemented the three Round267 pre-registered forecast/express disagreement candidates in the event PIT/IC prescreen path:

- `event_forecast_express_disagreement_1q`
- `event_forecast_express_disagreement_industry_relative_1q`
- `event_forecast_express_stale_forecast_correction_1q`

The implementation pairs each earnings express row with the latest prior forecast for the same `asset_id + end_date`, requiring `forecast_ann_date <= express_ann_date`. Signal dates are shifted to the first tradable date after the express event, with no same-day event trading.

## Long-Sample Run

- Command output: `data/reports/round268_forecast_express_disagreement_pit_ic_prescreen_20260626`
- Analysis window: 2015-01-01 through 2025-12-31
- Final holdout: excluded
- Horizons: 5 and 20 trading days
- Event rows: forecast 78,573; express 20,304
- Generated factor rows: 36,645
- Aligned rows: 68,835
- Tests: 6
- Research leads: 0
- Promotion candidates: 0

## Results

| Factor | Horizon | IC | ICIR | t | IC>0 | Q5-Q1 | Industry-neutral IC | Size-neutral IC | Year positive rate | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `event_forecast_express_stale_forecast_correction_1q` | 20 | -0.0317 | -0.191 | -1.43 | 32.1% | -0.0243 | 0.2878 | 0.0028 | 36.4% | no |
| `event_forecast_express_stale_forecast_correction_1q` | 5 | -0.0303 | -0.173 | -1.29 | 41.1% | -0.0104 | 0.3002 | -0.0073 | 36.4% | no |
| `event_forecast_express_disagreement_1q` | 20 | -0.0287 | -0.179 | -1.34 | 32.1% | -0.0208 | 0.2919 | 0.0067 | 36.4% | no |
| `event_forecast_express_disagreement_1q` | 5 | -0.0266 | -0.151 | -1.13 | 41.1% | -0.0087 | 0.2997 | -0.0010 | 36.4% | no |
| `event_forecast_express_disagreement_industry_relative_1q` | 20 | 0.0127 | 0.094 | 0.70 | 48.2% | -0.0024 | 0.3066 | 0.0346 | 54.5% | no |
| `event_forecast_express_disagreement_industry_relative_1q` | 5 | -0.0039 | -0.029 | -0.22 | 51.8% | -0.0025 | 0.3022 | 0.0068 | 54.5% | no |

## Audit Conclusion

This family should not move to portfolio construction. The raw and stale-correction variants have negative full-sample IC, negative quantile spreads, weak ICIR, and poor yearly sign stability. The industry-relative variant has a positive 20-day IC, but it is not statistically significant, still has negative Q5-Q1 spread, and fails the yearly stability and size-neutral gates.

The high industry-neutral IC is not enough to override the failed economic translation. It appears to capture a within-industry event ranking pattern, but that pattern did not convert into monotonic, positive, multiple-testing-adjusted forward returns.

## Next Direction

Round266-268 now form a completed three-round governance window. The next step is Round269 three-round review and family rotation decision, not more parameter tuning inside forecast/express disagreement.

Required next checks:

- Review Round266 direction gate, Round267 candidate pre-registration, and Round268 full-sample prescreen together.
- Hibernate forecast/express disagreement unless a genuinely new orthogonal hypothesis or data source is introduced.
- Select the next family from accessible sources only, with full-sample PIT replay required before any portfolio grid.
