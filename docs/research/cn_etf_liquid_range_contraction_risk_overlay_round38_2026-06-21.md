# CN ETF Range Contraction Risk Overlay Round38

Date: 2026-06-21

## Objective

Re-test the strongest current CN ETF research lead, `formula_range_contraction_breakout_20`, under risk controls instead of broadening to another blind factor family.

Two risk-control paths were checked:

1. Hard market-regime filter using benchmark positive momentum.
2. Lower gross exposure from 0.8 to 0.6 without deleting signal dates.

## Hard Regime Filter Preflight

Config: `configs/walk_forward_cn_etf_liquid_range_contraction_regime_round38_20260621.json`

The hard regime-filter design was blocked before walk-forward:

- Assets: 264 liquid CN ETFs.
- Dates: 1085.
- Folds: 4.
- Minimum rebalance opportunities: 26.
- Median regime-allowed rebalance dates: 1.0.
- Minimum allowed rebalance dates: 0.
- Zero-allowed folds: 2/4.
- Blockers:
  - `median_regime_allowed_rebalance_dates_below_minimum`
  - `zero_allowed_fold_rate_above_limit`

Lookback coverage diagnosis at 5-day rebalance:

| Lookback | Allowed Dates | Allowed Rate | Fold Counts | Zero Folds | Median Allowed |
|---:|---:|---:|---|---:|---:|
| 5 | 43 | 41.3% | 12, 10, 10, 11 | 0 | 10.5 |
| 10 | 40 | 38.5% | 14, 8, 8, 10 | 0 | 9.0 |
| 20 | 30 | 28.8% | 10, 6, 4, 10 | 0 | 8.0 |
| 40 | 30 | 28.8% | 9, 4, 2, 15 | 0 | 6.5 |
| 60 | 28 | 26.9% | 9, 4, 2, 13 | 0 | 6.5 |
| 90 | 23 | 22.1% | 14, 2, 0, 7 | 1 | 4.5 |
| 120 | 14 | 13.5% | 9, 2, 0, 3 | 1 | 2.5 |
| 180 | 14 | 13.5% | 7, 7, 0, 0 | 2 | 3.5 |
| 252 | 6 | 5.8% | 4, 1, 1, 0 | 1 | 1.0 |

Decision: do not run hard positive-momentum regime filtering on this ETF sample. It removes too much evidence and would create a low-power validation artifact.

## Exposure 0.6 Walk-Forward

Config: `configs/walk_forward_cn_etf_liquid_range_contraction_exposure06_round38_20260621.json`

Preflight cleared:

- Assets: 264.
- Dates: 1085.
- Folds: 4.
- Minimum allowed rebalance opportunities: 26.
- Median allowed rebalance opportunities: 26.
- Zero-allowed folds: 0.

Walk-forward:

- Cases: 12.
- Accepted: 0.
- Rejected: 12.
- Reason all strong rows remain rejected: adjusted IC significance did not pass after multiple-testing correction.

Top rows:

| Case | Accepted Folds | Sharpe | Ann. Return | Relative Return | Win Rate | Max DD | Adj. IC p |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb10` | 4/4 | 1.8334 | 1.43% | 6.03% | 56.25% | -0.18% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_20_top10_cost5_reb10` | 3/4 | 1.5847 | 3.01% | 6.77% | 66.67% | -1.73% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb5` | 3/4 | 1.5319 | 2.11% | 6.34% | 55.21% | -0.89% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_20_top10_cost5_reb5` | 2/4 | 1.5837 | 3.60% | 6.97% | 60.42% | -5.14% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb20` | 3/4 | 1.2799 | 0.45% | 5.57% | 58.33% | -0.27% | 1.0 |

Cost sensitivity:

| Cost | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return | Max Sharpe | Max Ann. Return |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 bps | 6 | 6 | 6 | 1.4518 | 2.02% | 6.29% | 1.8334 | 3.60% |
| 10 bps | 6 | 3 | 3 | -0.0724 | 0.24% | 5.45% | 0.8021 | 1.46% |

TopN sensitivity:

| TopN | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return | Max Sharpe | Max Ann. Return |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 6 | 3 | 3 | 0.3967 | 0.44% | 5.56% | 1.8334 | 2.11% |
| 10 | 6 | 6 | 6 | 0.9827 | 1.81% | 6.18% | 1.5847 | 3.60% |

Rebalance sensitivity:

| Rebalance | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return | Max Sharpe | Max Ann. Return | Max Accepted Folds |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 days | 4 | 3 | 3 | 0.7142 | 1.32% | 5.93% | 1.5837 | 3.60% | 3 |
| 10 days | 4 | 3 | 3 | 0.9664 | 1.45% | 6.04% | 1.8334 | 3.01% | 4 |
| 20 days | 4 | 3 | 3 | 0.3886 | 0.61% | 5.64% | 1.2799 | 1.53% | 3 |

## Interpretation

The range-contraction lead remains the only current ETF signal with a coherent positive cluster:

- 5 bps cost rows are all positive Sharpe and positive annualized return.
- Top10 is more stable on average than Top5.
- 10-day rebalance is the strongest balance of sample power, drawdown, and cost.
- No capacity-limited trades appeared.

But it still cannot be called a promotable profitable factor because:

- adjusted IC p-value remains 1.0,
- train performance is weak or mixed,
- 10 bps cost materially weakens results,
- the evidence period is still 2020-2024, not a longer structural validation.

## Decision

Do not promote.

Keep `formula_range_contraction_breakout_20` as the primary research lead for the next block.

Next required checks:

1. Long-cycle replay if older CN ETF data is available.
2. Same-parameter full-sample replay against the best 5 bps/10-day rows.
3. Composite tests that combine range contraction with liquid low-vol/high-liquidity tie-breakers, not hard regime deletion.
4. Avoid expanding to new public indicators until this lead either survives or fails the above robustness checks.
