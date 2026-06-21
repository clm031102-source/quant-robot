# CN Stock Public SuperTrend Bottom-Exclusion Walk-Forward Round82 - 2026-06-21

## Purpose

Round81 found one coherent SuperTrend-family research lead:

- `anti_supertrend_volume_confirmed_10_3_20`

The lead was not a direct buy factor. It had strong industry-neutral RankIC and a strong bottom-exclusion diagnostic, so Round82 tested the harder question:

Can the frozen anti-SuperTrend bottom-exclusion signal survive a costed rolling walk-forward portfolio gate?

No SuperTrend window, bottom quantile, rebalance interval, cost, exposure, or capacity threshold was tuned in this round.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Setup

- Market: CN stocks, not ETF rotation.
- Factor: `anti_supertrend_volume_confirmed_10_3_20`.
- Construction: exclude bottom 20%, hold the kept universe.
- Horizon: 20 trading days.
- Execution lag: 1.
- Rebalance interval: 10.
- Rolling train/test: 756 train days, 252 test days, 252 step days.
- Cost: 10 bps.
- Market impact: 20 bps.
- Max participation: 1% ADV.
- Min entry amount: 10,000,000.
- Portfolio value: 1,000,000.
- Target gross exposure: 0.6.
- Min accepted folds: 2.
- Min positive relative fold rate: 60%.
- Min test overlap-adjusted Sharpe: 0.5.
- Max test drawdown limit: 50%.

Config:

- `configs/experiment_grid_cn_stock_public_supertrend_exclusion_round82_20260621.json`

Output:

- `data/reports/bottom_exclusion_walk_forward_public_supertrend_anti_round82_20260621`

## Result

| Factor | Status | Accepted Folds | Mean Test Total | Mean Test Relative | Mean Test Overlap Sharpe | Worst Test DD | Mean Test Win Rate | Test Capacity-Limited Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `anti_supertrend_volume_confirmed_10_3_20` | rejected | 0/7 | -2.21% | 1.81% | -0.3693 | -22.00% | 47.22% | 0 |

Rejection reasons:

- `test_not_costed_risk_filter_candidate`
- `test_overlap_adjusted_sharpe_below_min`
- `accepted_folds_below_min`

Strict split:

- Status: pass.
- Violations: 0.

## Fold Detail

| Fold | Test Window | Test Total | Test Relative | Test Overlap Sharpe | Test DD | Test Win Rate | Test Classification |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 2018-02-05 to 2019-02-22 | -19.39% | 2.56% | -1.3735 | -22.00% | 26.74% | weak |
| 2 | 2019-02-25 to 2020-03-06 | 3.80% | 3.35% | 0.2526 | -11.73% | 45.90% | research lead |
| 3 | 2020-03-09 to 2021-03-19 | 11.44% | 2.26% | 0.4682 | -6.19% | 54.67% | research lead |
| 4 | 2021-03-22 to 2022-04-01 | 2.91% | 0.12% | 0.1939 | -8.04% | 54.29% | weak |
| 5 | 2022-04-06 to 2023-04-17 | -0.62% | 1.13% | -0.0370 | -7.97% | 51.92% | weak |
| 6 | 2023-04-18 to 2024-05-13 | -16.56% | 1.51% | -2.2504 | -18.17% | 40.38% | weak |
| 7 | 2024-05-14 to 2025-05-28 | 2.92% | 1.75% | 0.1613 | -11.37% | 56.67% | research lead |

## Interpretation

Positive evidence:

- Relative return was positive on average at 1.81%.
- Capacity was clean: 0 capacity-limited trades.
- Strict train/test split passed with 0 violations.
- Drawdown stayed inside the 50% absolute limit.
- Three folds had research-lead classifications.

Blocking evidence:

- Accepted folds were 0/7.
- Mean test total return was negative at -2.21%.
- Mean test overlap-adjusted Sharpe was -0.3693.
- The worst fold was poor: -19.39% total return and -1.3735 overlap-adjusted Sharpe.
- The best overlap-adjusted fold, 0.4682, still stayed below the 0.5 gate.
- The signal did not become a costed risk-filter candidate out of sample.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Manual/live usable factors: 0.

SuperTrend continuation candidates: 0.

Hibernate as promotion paths:

- raw `supertrend_volume_confirmed_10_3_20` direct TopN;
- `supertrend_volume_capacity_strict_10_3_20` direct TopN;
- `anti_supertrend_volume_confirmed_10_3_20` direct TopN;
- `anti_supertrend_volume_confirmed_10_3_20` bottom-exclusion walk-forward;
- any SuperTrend window, quantile, or exposure tuning after this zero-accepted-fold result.

Keep only as low-priority diagnostic reference:

- anti-SuperTrend can identify some bottom-tail risk, but not enough to justify more immediate compute.

## Next Direction

Round83 should rotate away from public technical indicators.

Next registered direction:

`round83_tushare_daily_basic_alpha_factory_replay`

Why:

- The repeated technical and public-formula signals mostly identify bad tails but do not create tradable long-only alpha.
- The existing project already has a Tushare daily-basic alpha factory with multiple-testing correction.
- The next useful check is whether the currently available Tushare daily-basic fields produce any adjusted-significant candidates under the stricter gate.
- If the available daily-basic fields are only PE/PB/PS/DV/turnover/market-cap style fields, the project should explicitly record the lack of true profitability-quality data rather than pretending to mine profitability factors from weak proxies.

Round83 constraints:

- use the existing alpha-factory gate or runner;
- keep Bonferroni/multiple-testing correction enabled;
- include cost, market impact, capacity controls, and min sample gates;
- do not promote IC-only rows;
- if no adjusted-significant candidate appears, record the data gap and rotate to Tushare financial-indicator ingestion/readiness before inventing more price-volume factors.
