# CN Stock Daily-Basic Residual Portfolio Round65

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Convert the Round64 daily-basic residual composite IC leads into a costed industry-neutral Top100 portfolio test. This round tests whether the signals can become a tradable long-only return engine after costs and capacity checks.

## Inputs

- Config: `configs/experiment_grid_cn_stock_daily_basic_residual_composite_round64_20260621.json`
- Factor source: `daily_basic_residual_composite`
- Factors: 3
- Selection: industry-neutral Top100
- Period: 2015-01-05 through 2025-12-31
- Forward horizon: 20
- Execution lag: 1
- Rebalance intervals: 5, 10
- Cost: 10 bps
- Market impact: 20 bps
- Max participation: 1% ADV
- Daily-basic input root: `configs/cn_stock_authority_daily_basic_inputs_2015_2025.json`
- Stock industry metadata: `data/processed/cn_stock_metadata`
- Output: `data/reports/industry_neutral_portfolio_daily_basic_residual_composite_round65_20260621`

## Portfolio Results

- Cases: 6
- Approved: 0
- Rejected: 6
- Capacity-limited cases: 0
- Best total return: 30.84%
- Best relative return: -2342.91%
- Best overlap-adjusted Sharpe: 0.1733
- Main reject reason: `relative_return_below_threshold`

| Factor | Rebalance | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Relative Return | Rank IC | Rank IC t | Tail IC | Tail IC t |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `resid_value_low_turnover_quality_20` | 10 | 24.12% | 1.45% | 0.1821 | 0.1733 | -32.57% | 53.03% | -2349.63% | 0.0381 | 3.98 | 0.0436 | 3.07 |
| `resid_value_reversal_low_tail_20` | 5 | 30.84% | 2.14% | 0.2871 | 0.1651 | -34.49% | 52.34% | -2342.91% | 0.0380 | 5.65 | 0.0434 | 4.45 |
| `resid_value_reversal_low_tail_20` | 10 | 16.74% | 1.08% | 0.1521 | 0.1475 | -33.32% | 52.34% | -2357.01% | 0.0371 | 3.82 | 0.0497 | 3.59 |
| `resid_value_low_turnover_quality_20` | 5 | 15.32% | 1.12% | 0.1721 | 0.1051 | -31.26% | 49.77% | -2358.42% | 0.0411 | 6.02 | 0.0498 | 5.21 |
| `resid_value_quality_low_vol_20` | 10 | 7.68% | 0.51% | 0.1029 | 0.0973 | -31.39% | 51.51% | -2366.07% | 0.0180 | 1.65 | 0.0488 | 3.52 |
| `resid_value_quality_low_vol_20` | 5 | 1.70% | 0.14% | 0.0588 | 0.0347 | -32.26% | 50.72% | -2372.05% | 0.0229 | 2.90 | 0.0577 | 6.01 |

## Interpretation

The family has real cross-sectional IC, but the IC did not convert into a profitable long-only portfolio. Capacity is not the blocker: all six cases had zero capacity-limited trades. The blocker is return conversion. The selected names are too defensive or too weak versus the long-cycle A-share benchmark, even after industry-neutral construction.

This is another example of a positive IC signal that may be useful as a risk filter or bottom-quantile exclusion layer, but is not a standalone buy signal. Expanding TopN, rebalance, or cost parameters now would be a waste-budget pattern unless the IC-to-portfolio gap is explained first.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- Costed long-only research lead: 0
- IC research leads retained for diagnostic: 2
  - `resid_value_low_turnover_quality_20`
  - `resid_value_reversal_low_tail_20`
- Rejected direction: `daily_basic_residual_industry_neutral_top100_long_only_promotion`
- Next step: run IC-to-portfolio gap and bottom-exclusion/quantile diagnostics before any further daily-basic residual family expansion
