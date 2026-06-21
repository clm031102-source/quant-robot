# CN ETF Liquid Public Formula Price-Volume Round32

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Objective

Rotate from tail-guard reversal to a public price-volume formula family on the liquid CN ETF universe. This round tests economically interpretable signals: price-volume divergence, volume contraction, range contraction breakout, and momentum-confirmed price-volume variants.

## Setup

- Config: `configs/walk_forward_cn_etf_liquid_public_formula_price_volume_round32_20260621.json`
- Data root: `data/processed/tushare_etf_wide_history_2023_2026`
- Universe: `data/reports/etf_liquid_universe_tushare_wide_2020_2024_round25/etf_liquid_universe.json`
- Market: `CN_ETF`
- Liquid universe size: 264 ETFs
- Date count: 1085 trading dates
- Benchmark: `CN_ETF_XSHG_510300`
- Walk-forward: 756 train days, 126 test days, 63 step days, 4 folds
- Portfolio: Top5, 80% gross exposure, 5 bps cost, 2 bps impact, 10% max participation
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
| 2 | `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb5` | 3/4 | 1.5298 | 2.83% | 6.68% | 55.21% | -1.19% | 1.0000 |
| 3 | `CN_ETF_formula_volume_contraction_momentum_confirmed_20_60_top5_cost5_reb5` | 3/4 | 0.5234 | 7.22% | 8.50% | 53.13% | -7.56% | 1.0000 |
| 4 | `CN_ETF_formula_volume_contraction_momentum_confirmed_20_60_top5_cost5_reb10` | 3/4 | 0.5521 | 2.26% | 6.35% | 56.25% | -6.06% | 1.0000 |
| 5 | `CN_ETF_formula_pv_corr_reversal_20_top5_cost5_reb5` | 1/4 | -0.2301 | -1.33% | 4.64% | 49.54% | -9.62% | 1.0000 |

Summary:

- Total cases: 10
- Accepted aggregate cases: 0
- Rejected cases: 10
- Strict split: passed on all cases
- Best family member: `formula_range_contraction_breakout_20`
- Main blocking reason for the best case: adjusted IC significance did not pass

## Audit Decision

This round produced a real research lead but not a promotable factor.

The range-contraction breakout variant is meaningfully better than the prior failed families on portfolio metrics: positive OOS return, positive relative return, 4/4 accepted folds for the rebalance-10 case, low drawdown, and no capacity limit flags. However, it still fails adjusted IC significance after multiple-testing correction, and the train-period portfolio Sharpe is weak. That combination suggests the result may be path-dependent or portfolio-construction-driven rather than a stable cross-sectional return predictor.

Direction decision:

- Keep `formula_range_contraction_breakout_20` as the first serious CN ETF research lead from this cycle.
- Do not promote it to paper/live.
- Round33 should run a constrained robustness grid on this single lead only, testing TopN, cost, and rebalance sensitivity without changing the factor formula.
- Deprioritize pure reversal and volume-contraction reversal variants unless they reappear through a stronger composite.

## Running Ledger

- Round26 trend-volume full sample: 0 promotable, weak research leads only.
- Round27 trend-volume regime WF: 0 promotable; regime config underpowered.
- Round28 trend-volume no-regime WF: 0 promotable; best weak research lead.
- Round29 basic momentum WF: 0 promotable.
- Round31 tail-guard reversal WF: 0 promotable; stop expanding this family.
- Round32 public formula price-volume WF: 0 promotable; one serious research lead (`formula_range_contraction_breakout_20`).
