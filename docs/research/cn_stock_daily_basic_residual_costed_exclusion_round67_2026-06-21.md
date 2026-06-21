# CN Stock Daily-Basic Residual Costed Exclusion Round67

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Run the Round64-66 stop-loss decision: only the two bottom-exclusion diagnostic candidates are allowed into a costed portfolio validation. This round tests whether the daily-basic residual family can become an investable risk filter after costs, impact, liquidity, capacity, and drawdown gates.

## Inputs

- Config: `configs/experiment_grid_cn_stock_daily_basic_residual_exclusion_candidates_round67_20260621.json`
- Factor source: `daily_basic_residual_composite`
- Factors:
  - `resid_value_low_turnover_quality_20`
  - `resid_value_reversal_low_tail_20`
- Bottom quantile: 20%
- Period: 2015-01-05 through 2025-12-31
- Holding period: 20
- Execution lag: 1
- Cost: 10 bps
- Market impact: 20 bps
- Max participation: 1% ADV
- Entry liquidity floor: 10,000,000 amount
- Portfolio value: 1,000,000

## Results

Outputs:

- `data/reports/bottom_exclusion_portfolio_daily_basic_residual_round67_20260621_reb5_liquid10m`
- `data/reports/bottom_exclusion_portfolio_daily_basic_residual_round67_20260621_reb10_liquid10m`

| Factor | Rebalance | Classification | Total | Benchmark | Relative | Gross | Sharpe | Overlap Sharpe | Max DD | Win | Positive Folds | Capacity |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `resid_value_low_turnover_quality_20` | 5 | research_lead_risk_filter | 40.12% | 26.32% | 13.80% | 82.27% | 0.1504 | 0.0826 | -63.57% | 48.16% | 9/11 | 0 |
| `resid_value_reversal_low_tail_20` | 5 | weak_or_unproven_risk_filter | 47.57% | 35.10% | 12.47% | 92.24% | 0.1668 | 0.0914 | -63.95% | 47.87% | 6/11 | 0 |
| `resid_value_low_turnover_quality_20` | 10 | research_lead_risk_filter | 37.59% | 23.56% | 14.03% | 79.00% | 0.1008 | 0.0748 | -64.16% | 49.05% | 8/11 | 0 |
| `resid_value_reversal_low_tail_20` | 10 | research_lead_risk_filter | 44.77% | 30.83% | 13.94% | 88.52% | 0.1101 | 0.0817 | -64.21% | 49.11% | 7/11 | 0 |

## Interpretation

The filters improve relative return and clear capacity, but they fail the investable risk-quality bar. The blocker is not signal direction or liquidity. The blocker is absolute risk: overlap-adjusted Sharpe is below 0.10 and maximum drawdown is around -64%.

This confirms the Round64-66 stop-loss rule. The daily-basic residual overlay line should not be expanded by more windows, thresholds, or TopN variants. Its useful lesson is methodological: bottom-tail exclusion can create relative improvement, but without a market-risk overlay it does not become a deployable CN stock factor.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- Costed risk-filter candidate: 0
- Research leads retained only as references: 2
- Active daily-basic residual line: hibernated
- Rejected direction: `daily_basic_residual_costed_exclusion_continuation_after_drawdown_failure`
- Next direction: `anti_obv_public_risk_regime_focus_batch`

Next work should use the existing `configs/experiment_grid_cn_stock_anti_obv_regime_focus_20260621.json` to test the strongest public risk-warning component under the formal regime-filtered TopN pipeline. If that also fails to solve absolute risk, the project should stop single-stock long-only risk-filter portfolios and move to a stock-to-ETF/breadth bridge or a TDD-built bottom-exclusion regime overlay.
