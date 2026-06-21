# CN ETF Liquid Public Trend-Volume Round 26

Date: 2026-06-21

## Purpose

Round 26 ran the first factor batch on the filtered CN ETF liquid-continuous universe from Round 25.

This was a discovery screen, not a promotion-grade validation.

## Config

Config:

- `configs/experiment_grid_cn_etf_liquid_public_trend_volume_round26_20260621.json`

Data:

- `data/processed/tushare_etf_wide_history_2023_2026`

Universe:

- `data/reports/etf_liquid_universe_tushare_wide_2020_2024_round25/etf_liquid_universe.json`
- Selected ETF assets: 264

Experiment grid:

- Factor source: `public_trend_volume`
- Factor names tested: 6
- Parameter cases: 48
- Window: 2020-01-02 to 2024-06-28
- Cost: 5 bps
- Execution lag: 1 day
- Forward horizon: 5 days
- Rebalance intervals: 5 and 10
- TopN: 5 and 10
- Regime lookbacks: 60 and 120
- Target gross exposure: 0.8
- Market impact: 2 bps
- Max participation rate: 10%

## Run Result

Output:

- `data/reports/experiment_grid_cn_etf_liquid_public_trend_volume_round26_20260621/leaderboard.csv`

Summary:

- Cases: 48
- Completed: 48
- Failed: 0
- No-trade: 0
- Positive relative return cases: 47
- Positive total return cases: 22
- Decision approved by current gate: 2
- Raw IC significance: 0 significant
- Tail IC significance: 2 significant positive, 1 significant negative

## Best Full-Sample Rows

These are research leads only. They are not promotable without walk-forward validation.

| Rank | Factor | TopN | Rebalance | Regime | Total | Relative | Sharpe | Adj Sharpe | Max DD | Win | IC t | RankIC t | Decision |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | supertrend_volume_confirmed_10_3_20 | 5 | 5 | 60 | 0.6903 | 0.8499 | 1.1852 | 1.3771 | -0.0880 | 0.5213 | 1.6908 | 2.0115 | rejected: capacity |
| 2 | obv_breakout_low_tail_20 | 5 | 5 | 60 | 0.6200 | 0.7795 | 1.0949 | 1.2437 | -0.0819 | 0.5106 | 0.7200 | 0.9214 | rejected: capacity |
| 3 | smart_money_trend_20 | 5 | 5 | 60 | 0.6096 | 0.7692 | 1.0566 | 1.2394 | -0.0894 | 0.5000 | 1.1088 | 0.5577 | rejected: capacity |
| 4 | supertrend_volume_confirmed_10_3_20 | 10 | 5 | 60 | 0.5205 | 0.6801 | 1.2859 | 1.5593 | -0.0791 | 0.5213 | 1.6908 | 2.0115 | rejected: capacity |
| 5 | obv_breakout_low_tail_20 | 10 | 5 | 60 | 0.4045 | 0.5641 | 1.0547 | 1.2554 | -0.0770 | 0.4894 | 0.7200 | 0.9214 | rejected: capacity |

Current gate-approved rows:

| Factor | TopN | Rebalance | Regime | Total | Relative | Sharpe | Max DD | Win | IC t | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| supertrend_volume_confirmed_10_3_20 | 5 | 10 | 60 | 0.3113 | 0.4709 | 0.7260 | -0.1829 | 0.5435 | 0.5104 | approved |
| supertrend_volume_confirmed_10_3_20 | 5 | 10 | 120 | -0.0599 | 0.0997 | -0.3682 | -0.1411 | 0.5161 | -0.0454 | approved |

## Interpretation

The filtered ETF universe improved the quality of the experiment:

- all 48 cases completed,
- the strongest rows have plausible public-market intuition,
- drawdowns on the best full-sample rows are much lower than earlier broad/narrow false positives.

But no factor is usable yet.

Reasons:

- No raw IC series is statistically significant.
- The highest-return rows are rejected by the capacity gate.
- One currently approved row has negative total return and negative Sharpe, exposing that the current gate is too weak.
- These are still full-sample discovery results, not walk-forward out-of-sample results.

## Decision

Promotable factors:

- 0

Research leads:

- `supertrend_volume_confirmed_10_3_20_top5_cost5_reb10_regime60`
- `supertrend_volume_confirmed_10_3_20_top5_cost5_reb5_regime60` as a small-capital/capacity diagnostic lead only
- `obv_breakout_low_tail_20_top5_cost5_reb5_regime60` as a small-capital/capacity diagnostic lead only

Do not mutate these parameters yet.

The next step should freeze the best candidates and run walk-forward validation plus a stricter promotion gate.
