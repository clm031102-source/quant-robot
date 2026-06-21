# CN Stock Dynamic Cash Overlay Round 72 - 2026-06-21

## Purpose

Round71 showed that static cash exposure scaling reduces drawdown mechanically but does not improve the quality of the return stream. Round72 tested whether a simple, pre-registered market-state cash overlay can turn the public risk-filter bridge research leads into tradable CN stock alpha.

The test deliberately reused the same factors, rebalance schedule, costs, liquidity floor, max participation, and long-cycle authority data. The only new translation layer was date-level exposure controlled by broad equal-weight market momentum.

## Setup

- Config: `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
- Factor source: `daily_basic_public_risk_filter_bridge`
- Factors:
  - `risk_filter_bridge_equal_20`
  - `risk_filter_bridge_agreement_20`
  - `risk_filter_bridge_anti_obv_weighted_20`
- Portfolio construction: exclude bottom 20%, hold the kept basket
- Rebalance: 10
- Holding period: 20
- Cost: 10 bps plus 20 bps market impact
- Liquidity floor: entry amount >= 10,000,000
- Portfolio value: 1,000,000
- Max participation: 1% ADV
- Target gross exposure: 0.6
- Execution lag: 1

## Dynamic Overlay Results

Best factor in each run: `risk_filter_bridge_anti_obv_weighted_20`.

| Market-State Lookback | Risk-Off Exposure | Risk-On Rate | Total Return | Relative Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Positive Relative Folds | Classification |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 0.0 | 56.96% | -15.84% | 6.24% | -0.0524 | -0.0411 | -52.12% | 30.90% | 10/11 | weak |
| 120 | 0.0 | 60.74% | 6.58% | 10.03% | 0.0531 | 0.0436 | -22.07% | 31.06% | 10/11 | research lead |
| 120 | 0.2 | 60.74% | 11.39% | 13.17% | 0.0748 | 0.0586 | -26.09% | 47.23% | 10/11 | research lead |

Outputs:

- `data/reports/dynamic_cash_overlay_public_risk_filter_round72_20260621_reb10_lb20_riskoff0`
- `data/reports/dynamic_cash_overlay_public_risk_filter_round72_20260621_reb10_lb120_riskoff0`
- `data/reports/dynamic_cash_overlay_public_risk_filter_round72_20260621_reb10_lb120_riskoff02`

## Interpretation

The dynamic overlay is useful as risk attribution evidence, not as a profitable factor result.

Positive evidence:

- The 120-day market-state overlay reduced max drawdown from the static 0.6 exposure drawdown of about -42.8% to -22.1% with risk-off 0.0 and -26.1% with risk-off 0.2.
- Relative return stayed positive across 10/11 yearly folds for the best factor.
- Capacity was clean in all dynamic overlay runs.
- The risk-off 0.2 version preserved more total return and win rate than the all-cash risk-off version.

Blocking evidence:

- No run met the overlap-adjusted Sharpe gate.
- Best overlap-adjusted Sharpe was only 0.0586, far below the 0.5 research candidate threshold.
- The 20-day overlay made absolute performance worse, which shows the market-state signal is lag-prone and parameter-sensitive.
- The 120-day overlay improves drawdown mostly by cutting beta exposure, not by proving a stronger stock-selection edge.
- The family remains relative-return defensive evidence, not standalone long-only alpha.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads:

- `risk_filter_bridge_anti_obv_weighted_20` remains useful only as a defensive risk-filter component.
- `risk_filter_bridge_agreement_20` and `risk_filter_bridge_equal_20` remain weaker defensive components.

Rejected direction:

- More dynamic cash-overlay parameter tuning around this same public risk-filter bridge family.

## Next Direction

Round73 should run a benchmark beta and market-state exposure diagnostic before hibernating or reusing this family.

Pre-registered question:

Is the public risk-filter bridge merely reducing exposure to weak broad-market regimes, or does it contain stock-selection alpha after controlling for market beta and market-state timing?

If the diagnostic shows that the edge is mostly beta/risk-off exposure, the public risk-filter bridge family should be hibernated and the next three-round cycle should rotate to a different public-method family with a cleaner expected return engine.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
