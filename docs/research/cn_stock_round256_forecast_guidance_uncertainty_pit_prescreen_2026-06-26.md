# CN Stock Round256 Forecast Guidance Uncertainty PIT Prescreen

## Scope

- Machine/task: `office_desktop` / `factor_validation`.
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`.
- Direction: rotate away from standalone moneyflow/forecast-express failure into a pre-registered, point-in-time event family.
- Family tested: `forecast_guidance_uncertainty`.
- Candidates: 3 factor names x horizons 5/20 = 6 tests.
- Promotion policy: research screen only; no portfolio grid, no broker/account/order access, no final holdout use.

## Method Optimization Applied

- A-share real tradeability: signal date is shifted to a later tradable date; same-day event trading is blocked.
- Financial/event PIT timing: forecast announcement date is used as the event timestamp, with `pit_lag_trade_days=1` and `execution_lag=1`.
- Industry/style neutralization: PIT screen records industry-neutral and size-neutral RankIC gates before any portfolio conversion.
- ETF boundary: this round is CN stock factor mining only, not CN ETF rotation.
- Portfolio construction: portfolio backtest remains blocked until PIT/IC, de-dup, walk-forward, cost/capacity, regime, and holdout gates clear.
- Strict statistics: Bonferroni/BH-FDR multiple-testing gate, ICIR, positive IC rate, quantile shape, and yearly stability are required.
- China market regime: no regime/promotion claim is allowed at this stage; later promotion must pass regime coverage.
- Event factors: cached forecast snapshot is used; live fetch drift is avoided.

## Data And Outputs

- Event cache: `data/processed/round255_forecast_express_event_cache_20260625`.
- Report output: `data/reports/round256_forecast_guidance_uncertainty_pit_ic_prescreen_20260626`.
- Data window: bars 2015-01-05 to 2025-12-31; labels to 2025-12-23; signals to 2025-12-30.
- Bar rows: 10,785,537 across 5,707 assets.
- Forecast event rows: 78,573.
- Factor rows: 221,376.
- Aligned rows: 399,834.
- Label rows: 21,417,227.

## Results

| Factor | Horizon | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `event_forecast_positive_floor_skew_1q` | 5 | 0.0182 | 0.111 | 2.21 | 53.8% | 0.0041 | 0.2779 | 0.0219 | no |
| `event_forecast_guidance_confidence_1q` | 20 | 0.0181 | 0.107 | 2.13 | 55.1% | 0.0135 | 0.2993 | 0.0305 | no |
| `event_forecast_positive_floor_skew_1q` | 20 | 0.0176 | 0.106 | 2.11 | 54.8% | 0.0105 | 0.2789 | 0.0300 | no |
| `event_forecast_guidance_confidence_1q` | 5 | 0.0171 | 0.105 | 2.09 | 53.3% | 0.0054 | 0.2997 | 0.0225 | no |
| `event_forecast_uncertainty_compression_1q` | 5 | 0.0084 | 0.058 | 1.16 | 50.5% | -0.0007 | 0.2680 | 0.0133 | no |
| `event_forecast_uncertainty_compression_1q` | 20 | 0.0038 | 0.025 | 0.50 | 52.8% | -0.0033 | 0.2694 | 0.0128 | no |

Summary:

- Research leads: 0.
- FDR-significant tests: 0.
- Promotion-allowed candidates: 0.
- Neutral-gate pass tests: 4, but this is not sufficient because raw IC, ICIR, FDR, and yearly stability fail.
- Yearly coverage/stability pass tests: 1.

## Audit Conclusion

This round is useful as process optimization and negative evidence, not as a profitable factor result. The best raw IC is only 0.0182 and the best ICIR is only 0.111, well below the research gate. The family has weak quantile shape and fails multiple-testing significance, so expanding thresholds, flipping signs, or moving directly into TopN portfolio grids would be data mining.

The correct action is to hibernate `forecast_guidance_uncertainty_after_round256_zero_research_leads` and rotate Round257 to a non-forecast, orthogonal family that still starts from the same long-cycle PIT/neutral/statistical controls.

## Engineering Changes

- Added reusable forecast-guidance uncertainty factors to `event_factor_pit_ic_prescreen`.
- Added `scripts/run_forecast_guidance_uncertainty_pit_ic_prescreen.py`.
- Added tests for PIT factor formulas and the Round256 runner.
- Fixed event PIT/IC report metadata so a new round can pass its own report title and next-direction labels instead of inheriting old Round147 text.
- Updated `configs/factor_mining_startup_cn_stock.json` so the next startup gate points to Round257 rotation and blocks Round256 family re-entry.
