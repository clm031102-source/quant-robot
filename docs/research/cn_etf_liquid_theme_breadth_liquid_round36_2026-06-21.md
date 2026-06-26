# CN ETF Liquid Theme Breadth Liquid Round36

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Objective

Fix and test the main Round35 failure mode: raw theme scores tie all ETFs inside the same theme, which can make TopN select less tradable ETF members. Round36 adds liquid tie-break variants to theme breadth/strength factors and validates whether the theme direction becomes tradable and profitable.

## Implementation

Added liquid-adjusted theme variants in `src/quant_robot/factors/etf_theme_breadth.py`:

- `theme_relative_strength_liquid_<window>`
- `theme_rank_strength_liquid_<window>`
- `theme_risk_adjusted_strength_liquid_<window>`

The liquid variants keep the theme signal but add a small same-day/past-only ADV amount z-score tie-breaker. This is meant to prefer more tradable ETF representatives when multiple ETFs share the same theme score.

Verification:

- `python -m unittest tests.unit.test_etf_theme_breadth`
- `python -m unittest tests.unit.test_experiment_runner tests.unit.test_project_audit`
- Result: all passed

## Setup

- Config: `configs/walk_forward_cn_etf_liquid_theme_breadth_liquid_round36_20260621.json`
- Data root: `data/processed/tushare_etf_wide_history_2023_2026`
- Theme metadata root: `data/processed/tushare_etf_wide_history_2023_2026`
- Universe: `data/reports/etf_liquid_universe_tushare_wide_2020_2024_round25/etf_liquid_universe.json`
- Market: `CN_ETF`
- Walk-forward: 756 train days, 126 test days, 63 step days, 4 folds
- Portfolio: Top5, 80% gross exposure, 5 bps cost, 2 bps impact, 10% max participation
- Cases: 10

## Results

| Rank | Case | Accepted folds | Mean test Sharpe | Mean ann. return | Mean relative return | Mean win rate | Test max DD | Capacity-limited trades | Adjusted IC p |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `CN_ETF_theme_rank_strength_liquid_20_top5_cost5_reb5` | 1/4 | -0.3158 | -3.31% | 3.68% | 47.92% | -12.10% | 0 | 1.0000 |
| 2 | `CN_ETF_theme_risk_adjusted_strength_liquid_60_top5_cost5_reb5` | 0/4 | -0.4314 | -4.94% | 2.96% | 52.08% | -10.65% | 0 | 1.0000 |
| 3 | `CN_ETF_theme_risk_adjusted_strength_liquid_20_top5_cost5_reb5` | 2/4 | -0.5772 | -7.52% | 1.51% | 45.83% | -17.57% | 0 | 1.0000 |
| 4 | `CN_ETF_theme_relative_strength_liquid_60_top5_cost5_reb5` | 1/4 | -0.8151 | -8.19% | 1.34% | 44.79% | -13.08% | 0 | 1.0000 |
| 5 | `CN_ETF_theme_risk_adjusted_strength_liquid_60_top5_cost5_reb10` | 1/4 | -0.5313 | -8.37% | 0.98% | 50.00% | -15.70% | 0 | 1.0000 |

Summary:

- Total cases: 10
- Accepted aggregate cases: 0
- Positive annualized return: 0/10
- Positive Sharpe: 0/10
- Capacity-limited cases: 0/10
- Maximum capacity-limited trades: 0

## Audit Decision

The engineering fix worked, but the alpha did not.

The liquid tie-break removed capacity-limited trades completely, so the Round35 execution problem was real and fixed. However, all liquid-adjusted theme variants still had negative Sharpe and negative annualized return. This means current keyword-based theme breadth/strength is not a useful standalone CN ETF rotation signal.

Direction decision:

- Keep the liquid theme variants as infrastructure because they solve a real capacity/tie issue.
- Stop expanding standalone theme breadth in this cycle.
- Do not combine theme breadth with `formula_range_contraction_breakout_20` yet; a failed standalone signal with no positive Sharpe is more likely to add noise.
- Next block should prioritize defensive/low-volatility/liquidity ETF rotation and risk-state validation around the existing range-contraction breakout lead.
