# CN Stock Tushare Daily-Basic Alpha Factory Core Round83 - 2026-06-21

## Purpose

Round83 rotated away from the failed SuperTrend line and replayed a core Tushare `daily_basic` factor batch on the full CN stock authority dataset.

This was not a short-sample search. It used the 2015-01-05 to 2025-12-31 authority bars and matching Tushare daily-basic factor inputs, with execution lag, cost, market impact, capacity controls, and overlap-aware statistics.

## Setup

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Data: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
- Daily-basic inputs: `configs/cn_stock_authority_daily_basic_inputs_2015_2025.json`
- Data manifest: `data/reports/cn_stock_data_manifest_round83_daily_basic/cn_stock_data_manifest.json`
- Config: `configs/experiment_grid_cn_stock_tushare_daily_basic_alpha_factory_core_round83_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_tushare_daily_basic_alpha_factory_core_round83_20260621`

Data manifest evidence:

- Bar rows: 8,416,451
- Bar symbols: 4,725
- Daily-basic rows: 10,700,940
- Daily-basic symbols: 5,707
- Date range: 2015-01-05 to 2025-12-31
- Blockers: none
- Warning: `extreme_return_rows_present`

Grid parameters:

- Factor source: `tushare_daily_basic`
- Factors: 12 core value/liquidity/dividend/size-capacity factors
- TopN: 100
- Forward horizon: 20 trading days
- Rebalance interval: 5 trading days
- Execution lag: 1
- Cost: 10 bps
- Market impact: 20 bps
- Max participation: 1% ADV
- Portfolio value: 1,000,000
- Rank metric: `overlap_autocorr_adjusted_sharpe`
- Precompute factor matrix: enabled
- Reuse research inputs: enabled

The monolithic `scripts/run_tushare_alpha_factory.py` path was also tested first, but it timed out after 30 minutes while only producing a few partial cases. Round83 therefore fixed the common research loader so authority config files can be used by alpha factory paths, then used the faster experiment-grid execution path for the completed batch.

## Result

- Cases: 12
- Completed: 12
- Failed: 0
- No-trade: 0
- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0

## Leaderboard

| Rank | Factor | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Mean RankIC | IC t | Relative Return | Capacity Limited | Extreme Flag | Decision |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | `turnover_rate_low` | 5127.61% | 21.25% | 1.983 | 0.961 | -18.43% | 59.32% | 0.1028 | 14.99 | 2753.86% | 1437 | true | rejected |
| 2 | `turnover_rate_f_low` | 5318.72% | 19.86% | 1.872 | 0.902 | -28.56% | 57.43% | 0.1079 | 17.03 | 2944.97% | 1641 | true | rejected |
| 3 | `dv_ttm` | 181.01% | 6.79% | 0.842 | 0.478 | -29.54% | 54.98% | 0.0465 | 3.41 | -2192.73% | 76 | false | rejected |
| 4 | `ps_ttm_inverse` | 178.33% | 5.24% | 0.623 | 0.348 | -35.15% | 50.64% | 0.0459 | 2.50 | -2195.42% | 7 | false | rejected |
| 5 | `dv_ttm_large_mv` | 98.24% | 4.35% | 0.607 | 0.340 | -34.78% | 53.58% | 0.0066 | -0.39 | -2275.51% | 2 | false | rejected |
| 6 | `pe_ttm_inverse` | 108.95% | 4.10% | 0.541 | 0.308 | -27.27% | 51.19% | 0.0462 | 1.96 | -2264.80% | 6 | true | rejected |
| 7 | `pb_inverse` | 131.30% | 4.66% | 0.567 | 0.303 | -28.87% | 47.46% | 0.0615 | 3.26 | -2242.45% | 15 | true | rejected |
| 8 | `ps_ttm_inverse_large_mv` | 108.30% | 3.88% | 0.528 | 0.295 | -36.15% | 53.29% | -0.0073 | -3.84 | -2265.45% | 1 | false | rejected |
| 9 | `turnover_rate_f_low_large_mv` | 79.94% | 3.45% | 0.529 | 0.279 | -35.25% | 51.32% | 0.0421 | 3.78 | -2293.81% | 0 | false | rejected |
| 10 | `turnover_rate_low_large_mv` | 66.78% | 2.97% | 0.457 | 0.244 | -36.59% | 52.16% | 0.0339 | 3.16 | -2306.96% | 0 | false | rejected |
| 11 | `circ_mv_log` | 45.27% | 2.10% | 0.336 | 0.179 | -38.25% | 51.66% | -0.0270 | -6.24 | -2328.48% | 0 | false | rejected |
| 12 | `volume_ratio_low` | 55.09% | 1.93% | 0.270 | 0.143 | -58.19% | 47.66% | 0.0084 | 6.43 | -2318.66% | 397 | false | rejected |

## Interpretation

The brightest data in this round is also the most dangerous:

- `turnover_rate_low` and `turnover_rate_f_low` have huge full-sample total return, Sharpe near 2, overlap-adjusted Sharpe near 0.9-1.0, positive IC, positive tail IC, and positive benchmark-relative return.
- They are still not promotable because both have many capacity-limited trades and `extreme_trade_return_flag=true`.
- The capacity-aware large-market-cap variants remove the capacity problem, but the return collapses: `turnover_rate_f_low_large_mv` has 0 capacity-limited trades but only 79.94% total return, 0.279 overlap-adjusted Sharpe, and large negative relative return.

So the likely signal is not "low turnover is ready to trade." The more precise conclusion is:

> A low-turnover/liquidity anomaly exists in the long-cycle data, but the tradable version may be much weaker than the raw version. Before any promotion, it needs capacity-clean replay, extreme-trade attribution, and walk-forward validation.

## Decision

No Round83 daily-basic factor is promotable.

Keep as research leads only:

- `turnover_rate_low`
- `turnover_rate_f_low`

But they are frozen for diagnostics, not expansion. Do not run more TopN/window sweeps until the following questions are answered:

- Are the huge returns driven by a small number of extreme trade events?
- Are capacity-limited trades concentrated in tiny, illiquid names?
- Does the signal survive after removing capacity-limited trades or enforcing a larger minimum liquidity universe?
- Does the signal survive rolling walk-forward folds?
- Does the signal remain positive after industry/size neutralization?

## Next Direction

Round84 should be:

`round84_daily_basic_low_turnover_capacity_extreme_trade_diagnostic`

Required scope:

- Frozen factors only: `turnover_rate_low` and `turnover_rate_f_low`.
- Diagnose all extreme trades and top contribution trades.
- Rerun with capacity-limited trades removed or blocked.
- Compare raw low-turnover against capacity-clean and large-market variants.
- Do not promote unless capacity-clean walk-forward passes.
