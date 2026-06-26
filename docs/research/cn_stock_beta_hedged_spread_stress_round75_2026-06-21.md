# CN Stock Beta-Hedged Spread Stress Round 75 - 2026-06-21

## Purpose

Round74 rejected the fixed 1.0 beta-hedged spread after correcting the short benchmark-leg cost sign. Round75 reran the same spread translation layer under harsher transaction-cost stress to confirm whether the rejection is robust.

## Setup

- Config: `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
- Spread construction: kept basket minus 1.0 * equal-weight benchmark basket
- Rebalance: 10
- Holding period: 20
- Cost: 30 bps
- Market impact: 50 bps
- Liquidity floor: entry amount >= 10,000,000
- Portfolio value: 1,000,000
- Max participation: 1% ADV
- Target gross exposure: 0.6

Output:

- `data/reports/beta_hedged_spread_public_risk_filter_round75_20260621_reb10_hedge1_cost30_impact50`

## Results

| Factor | Classification | Spread Total | Spread Sharpe | Overlap Sharpe | Max DD | Win Rate | Positive Folds | NW t-stat | Capacity Limited |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_equal_20` | weak | -54.41% | -1.9838 | -1.7010 | -54.14% | 34.96% | 0/11 | -12.6468 | 0 |
| `risk_filter_bridge_anti_obv_weighted_20` | weak | -53.74% | -2.0173 | -1.7338 | -53.50% | 35.10% | 0/11 | -12.8905 | 0 |
| `risk_filter_bridge_agreement_20` | weak | -54.28% | -2.1004 | -1.7386 | -54.05% | 33.74% | 0/11 | -12.9266 | 0 |

## Interpretation

The stress test confirms the rejection.

The public risk-filter bridge family has useful diagnostic information, but the attempted executable translation layers failed:

- long-only static exposure scaling failed;
- dynamic cash overlay failed promotion gates;
- benchmark beta diagnostic found a residual spread but not a standalone portfolio;
- corrected fixed-ratio hedge failed;
- harsher cost/impact stress strongly failed.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Stress-surviving spread candidates: 0.

Hibernation decision:

- Hibernate the public risk-filter bridge family as a promotion path.
- Keep the tools and evidence because they are useful for future translation-layer audits.

## Next Direction

Round76 should rotate to a different public-method family instead of spending more budget on this one.

The next family should be pre-registered from public, economically interpretable methods and tested through the full long-cycle, cost, capacity, overlap, fold, and no-lookahead gates before any candidate claim.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
