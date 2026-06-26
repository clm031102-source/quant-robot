# CN Stock Benchmark Beta Exposure Round 73 - 2026-06-21

## Purpose

Round71 and Round72 showed that the public risk-filter bridge family can reduce weak tails and drawdown, but it still fails as a standalone long-only alpha portfolio. Round73 tested whether the remaining edge is just broad market beta/cash timing, or whether there is a measurable stock-selection spread after controlling for the equal-weight benchmark basket.

This is a diagnostic audit, not promotion evidence.

## Setup

- Config: `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
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
- Dynamic overlay: 120-day equal-weight market momentum, risk-off exposure 0.2

Output:

- `data/reports/benchmark_beta_exposure_public_risk_filter_round73_20260621_reb10_lb120_riskoff02`

## Results

| Factor | Classification | Dynamic Total | Dynamic Beta | Dynamic R2 | Dynamic Alpha t | Dynamic Residual Sharpe | Dynamic Beta-Adjusted Total | Static Alpha t | Static Residual Sharpe |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_agreement_20` | research lead with beta | 10.69% | 0.9937 | 0.9939 | 5.4210 | 0.7597 | 12.63% | 6.0980 | 0.8546 |
| `risk_filter_bridge_anti_obv_weighted_20` | research lead with beta | 11.39% | 0.9778 | 0.9927 | 5.2143 | 0.7368 | 13.03% | 6.1195 | 0.8647 |
| `risk_filter_bridge_equal_20` | research lead with beta | 9.77% | 0.9759 | 0.9919 | 4.3926 | 0.6202 | 11.51% | 5.3648 | 0.7575 |

## Interpretation

This family is not empty noise, but it is not yet a tradable long-only factor.

Positive evidence:

- All three factors show positive beta-adjusted total return after controlling for the equal-weight benchmark basket.
- Dynamic residual alpha t-stat is above 4.3 for all three factors.
- Dynamic residual Sharpe is above 0.62 for all three factors.
- The result is consistent with the previous bottom-exclusion interpretation: the factor is better at removing weak names than selecting a high-return long-only top basket.

Blocking evidence:

- Dynamic R2 is above 0.991 for all three factors, so the realized long-only return stream is still overwhelmingly market/basket beta.
- Round72 raw portfolio quality remains poor: best dynamic overlap-adjusted Sharpe was only 0.0586.
- Dynamic drawdown is still around -26% even after the cash overlay.
- The diagnostic uses a same-family equal-weight benchmark; the residual spread may be too small or hard to monetize after realistic hedge, shorting, borrow, or execution constraints.
- This does not satisfy the project promotion gate for profitable long-only factors.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads:

- `risk_filter_bridge_agreement_20`: best beta-adjusted t-stat in the dynamic audit.
- `risk_filter_bridge_anti_obv_weighted_20`: best total return and beta-adjusted total return in the dynamic audit.

Rejected direction:

- More long-only cash-overlay or market-state parameter tuning for this same family.

## Next Direction

The only justified continuation is a translation-layer test, not another factor parameter expansion.

Pre-registered next question:

Can the residual spread from this family survive a realistic beta-hedged or long-short-style audit after costs, turnover, drawdown, and capacity controls?

If the beta-hedged spread audit fails, the public risk-filter bridge family should be hibernated and the next mining cycle should rotate to a different public-method family with a clearer expected return engine.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
