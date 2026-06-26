# CN ETF Liquid Theme Breadth Round35

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Objective

Test ETF-specific theme breadth and theme strength factors on the liquid CN ETF universe, using the Round34 Tushare `fund_basic` metadata snapshot.

## Setup

- Config: `configs/walk_forward_cn_etf_liquid_theme_breadth_round35_20260621.json`
- Data root: `data/processed/tushare_etf_wide_history_2023_2026`
- Theme metadata root: `data/processed/tushare_etf_wide_history_2023_2026`
- Universe: `data/reports/etf_liquid_universe_tushare_wide_2020_2024_round25/etf_liquid_universe.json`
- Market: `CN_ETF`
- Liquid universe size: 264 ETFs
- Theme coverage: 252/264 liquid-universe ETFs
- Walk-forward: 756 train days, 126 test days, 63 step days, 4 folds
- Portfolio: Top5, 80% gross exposure, 5 bps cost, 2 bps impact, 10% max participation
- Factors: 6 theme breadth/strength factors across 20d/60d windows
- Cases: 12

## Results

| Rank | Case | Accepted folds | Mean test Sharpe | Mean ann. return | Mean relative return | Mean win rate | Test max DD | Capacity-limited trades | Adjusted IC p |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `CN_ETF_theme_rank_strength_20_top5_cost5_reb5` | 1/4 | -0.2669 | -3.69% | 3.51% | 46.88% | -11.66% | 7 | 1.0000 |
| 2 | `CN_ETF_theme_relative_strength_20_top5_cost5_reb5` | 1/4 | -0.2669 | -3.69% | 3.51% | 46.88% | -11.66% | 7 | 1.0000 |
| 3 | `CN_ETF_theme_momentum_breadth_20_top5_cost5_reb5` | 1/4 | -0.3118 | -5.92% | 2.45% | 50.00% | -12.01% | 9 | 1.0000 |
| 4 | `CN_ETF_theme_risk_adjusted_strength_20_top5_cost5_reb5` | 2/4 | -0.5288 | -7.33% | 1.60% | 44.79% | -17.15% | 17 | 1.0000 |
| 5 | `CN_ETF_theme_risk_adjusted_strength_60_top5_cost5_reb5` | 0/4 | -0.8446 | -9.00% | 0.96% | 45.83% | -12.52% | 18 | 1.0000 |

Summary:

- Total cases: 12
- Accepted aggregate cases: 0
- Positive annualized return: 0/12
- Positive Sharpe: 0/12
- Capacity-limited cases: 12/12
- Maximum capacity-limited trades in one case: 18

## Audit Decision

Raw theme breadth/strength is not useful as currently implemented.

The negative result is informative rather than just another failed factor family. Theme-level scores are identical for all ETFs inside the same theme. A TopN selector can therefore choose lower-liquidity members within a strong theme because the factor value ties. The capacity-limited flags across all 12 cases are consistent with this failure mode.

Direction decision:

- Do not expand raw theme breadth parameters.
- Add a liquid tie-break variant for theme breadth/strength so a strong theme selects its more tradable ETF representatives.
- Round36 should validate only the liquid-adjusted theme variants, then audit whether theme context is still worth combining with `formula_range_contraction_breakout_20`.
