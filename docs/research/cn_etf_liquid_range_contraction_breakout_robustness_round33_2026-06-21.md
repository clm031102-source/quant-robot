# CN ETF Liquid Range-Contraction Breakout Robustness Round33

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Objective

Run a constrained robustness test on the Round32 lead `formula_range_contraction_breakout_20`. This round does not introduce new factor formulas. It only varies portfolio breadth, cost, and rebalance interval to test whether the signal is robust or just a single parameter accident.

## Setup

- Config: `configs/walk_forward_cn_etf_liquid_range_contraction_breakout_robustness_round33_20260621.json`
- Data root: `data/processed/tushare_etf_wide_history_2023_2026`
- Universe: `data/reports/etf_liquid_universe_tushare_wide_2020_2024_round25/etf_liquid_universe.json`
- Market: `CN_ETF`
- Liquid universe size: 264 ETFs
- Date count: 1085 trading dates
- Benchmark: `CN_ETF_XSHG_510300`
- Walk-forward: 756 train days, 126 test days, 63 step days, 4 folds
- Tested grid: TopN 3/5/10, cost 5/10 bps, rebalance 5/10/20
- Multiple-testing alpha: 0.05

## Preflight

ETF validation preflight cleared.

- Fold count: 4
- Median allowed rebalance dates: 26
- Minimum allowed rebalance dates: 26
- Zero-allowed fold count: 0
- Blockers: none

## Results

| Rank | Case | Accepted folds | Mean test Sharpe | Mean ann. return | Mean relative return | Mean win rate | Test max DD | Adjusted IC p |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb10` | 4/4 | 1.8316 | 1.91% | 6.26% | 56.25% | -0.24% | 1.0000 |
| 2 | `CN_ETF_formula_range_contraction_breakout_20_top10_cost5_reb10` | 3/4 | 1.5841 | 4.03% | 7.24% | 66.67% | -2.30% | 1.0000 |
| 3 | `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb5` | 3/4 | 1.5298 | 2.83% | 6.68% | 55.21% | -1.19% | 1.0000 |
| 4 | `CN_ETF_formula_range_contraction_breakout_20_top10_cost5_reb5` | 2/4 | 1.5831 | 4.96% | 7.53% | 60.42% | -6.81% | 1.0000 |
| 5 | `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb20` | 3/4 | 1.2783 | 0.61% | 5.64% | 58.33% | -0.36% | 1.0000 |

Aggregate robustness checks:

- Total cases: 18
- Accepted aggregate cases: 0
- Positive annualized return: 10/18
- Positive Sharpe: 9/18
- Accepted folds >= 3: 7/18
- Cost 5 bps average Sharpe: 0.6283
- Cost 5 bps average annualized return: 1.73%
- Cost 5 bps average relative return: 6.15%
- Cost 10 bps average Sharpe: -1.6052
- Cost 10 bps average annualized return: -0.63%
- Cost 10 bps average relative return: 5.03%
- Top10 average Sharpe: 0.9822
- Top5 average Sharpe: 0.3949
- Top3 average Sharpe: -2.8424

## Audit Decision

This is a stronger research lead than the prior families, but it is still not promotable.

Evidence in favor:

- The best 5 bps cases form a small positive cluster rather than a single isolated result.
- Top5 and Top10 both work better than Top3, suggesting the edge is not purely one lucky ETF.
- Drawdowns are low in the best cases.
- Capacity flags remain clear.

Evidence against promotion:

- Every case still fails adjusted IC significance.
- Cost sensitivity is severe: the 10 bps grid average Sharpe turns negative.
- Top3 performs poorly, so concentrated deployment is not robust.
- The signal may be a portfolio construction/risk-state effect rather than a stable cross-sectional predictor.

Decision:

- Keep `formula_range_contraction_breakout_20` as a pre-registered research candidate.
- Do not promote to paper/live.
- Next work should test whether this lead improves when combined with ETF-specific theme breadth/risk-on context, not by adding more price-volume parameters.
