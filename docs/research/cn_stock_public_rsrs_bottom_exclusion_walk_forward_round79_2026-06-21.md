# CN Stock Public RSRS Bottom-Exclusion Walk-Forward Round 79 - 2026-06-21

## Purpose

Round78 found that `rsrs_reversal_18_60` had strong industry-neutral RankIC and a promising bottom-exclusion diagnostic overlay. Round79 tested the harder question:

Can the frozen RSRS reversal bottom-exclusion signal survive a costed rolling walk-forward portfolio gate?

No RSRS windows, bottom quantile, cost assumptions, or exposure parameters were tuned in this round.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Setup

- Market: CN stocks, not ETF rotation.
- Factor: `rsrs_reversal_18_60`.
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
- Min test overlap-adjusted Sharpe: 0.5.
- Max test drawdown limit: 50%.

Output:

- `data/reports/bottom_exclusion_walk_forward_public_rsrs_reversal_round79_20260621`

## Engineering Output

Round79 added a reusable bottom-exclusion rolling walk-forward tool:

- `src/quant_robot/ops/bottom_exclusion_walk_forward.py`
- `scripts/run_bottom_exclusion_walk_forward.py`
- `tests/unit/test_bottom_exclusion_walk_forward.py`

The tool enforces strict train/test date separation and writes:

- `bottom_exclusion_walk_forward.json`
- `bottom_exclusion_walk_forward.md`
- `walk_forward_leaderboard.csv`
- `walk_forward_folds.csv`

## Result

| Factor | Status | Accepted Folds | Mean Test Total | Mean Test Relative | Mean Test Overlap Sharpe | Worst Test DD | Test Capacity-Limited Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| `rsrs_reversal_18_60` | rejected | 0/7 | 2.86% | 0.46% | 0.0766 | -17.90% | 0 |

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
| 1 | 2018-02-05 to 2019-02-22 | -10.89% | 0.56% | -0.3787 | -17.90% | 31.84% | weak |
| 2 | 2019-02-25 to 2020-03-06 | 5.82% | 1.16% | 0.2501 | -9.82% | 43.97% | research lead |
| 3 | 2020-03-09 to 2021-03-19 | 7.50% | 0.80% | 0.2853 | -8.03% | 56.55% | research lead |
| 4 | 2021-03-22 to 2022-04-01 | 6.56% | -0.02% | 0.3643 | -6.18% | 64.79% | weak |
| 5 | 2022-04-06 to 2023-04-17 | 8.54% | 0.15% | 0.4481 | -5.04% | 53.24% | weak |
| 6 | 2023-04-18 to 2024-05-13 | -13.93% | -0.30% | -0.7784 | -17.59% | 48.11% | weak |
| 7 | 2024-05-14 to 2025-05-28 | 16.45% | 0.91% | 0.3454 | -7.77% | 61.79% | weak |

## Interpretation

Positive evidence:

- Mean test relative return is positive at 0.46%.
- Capacity is clean after the 10,000,000 entry-amount gate.
- Worst test drawdown is only -17.90%, inside the absolute drawdown limit.
- Several test windows have positive absolute return.

Blocking evidence:

- 0/7 test folds cleared the costed risk-filter gate.
- Mean test overlap-adjusted Sharpe is only 0.0766, far below the 0.5 threshold.
- Two folds had negative absolute test return.
- The best diagnostic overlay from Round78 does not survive as a robust walk-forward portfolio.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

RSRS continuation candidates: 0.

Hibernate as promotion paths:

- `public_rsrs` direct TopN;
- `public_rsrs` industry-neutral TopN;
- `rsrs_reversal_18_60` bottom-exclusion walk-forward;
- RSRS window, quantile, or exposure tuning after this zero-accepted-fold result.

Keep only as low-priority diagnostic reference:

- RSRS reversal may contain weak relative-return information, but not enough to justify more immediate compute.

## Next Direction

Round80 should package lightweight results and run the GitHub safe-sync cadence before new factor-family mining.

After sync, rotate to a new public-method family:

`public_supertrend_exclusion_preregistration`

Pre-registered direction:

- Use ATR/SuperTrend-style public trend state as a cross-sectional risk/exclusion signal.
- Test both direction and reversal before portfolio expansion.
- Run signal-direction/IC and bottom-exclusion diagnostics before any wide TopN grid.
- Do not repeat RSRS-style parameter expansion without a new return engine.
