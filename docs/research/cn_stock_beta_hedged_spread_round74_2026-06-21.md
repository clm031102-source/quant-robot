# CN Stock Beta-Hedged Spread Round 74 - 2026-06-21

## Purpose

Round73 found that the public risk-filter bridge family contains a measurable residual spread after equal-weight benchmark control, but the long-only return stream is still dominated by basket beta. Round74 tested the simplest translation layer:

`kept basket return - 1.0 * equal-weight benchmark basket return`

No hedge-ratio optimization was used. The goal was to avoid turning the beta diagnostic into another parameter search.

## Implementation Note

The first Round74 run exposed a cost-sign bug in the new spread tool: using `selected_net - benchmark_net` incorrectly added short benchmark-leg costs back into the spread. The tool was fixed so the short benchmark leg is now:

`-benchmark_gross_return - benchmark_cost`

The results below are from the corrected implementation. The earlier positive spread-candidate read is invalid.

## Setup

- Config: `configs/experiment_grid_cn_stock_composite_risk_filter_bridge_fast_20260621.json`
- Factors:
  - `risk_filter_bridge_equal_20`
  - `risk_filter_bridge_agreement_20`
  - `risk_filter_bridge_anti_obv_weighted_20`
- Portfolio construction: exclude bottom 20%, hold the kept basket
- Spread construction: kept basket minus 1.0 * equal-weight benchmark basket
- Rebalance: 10
- Holding period: 20
- Cost: 10 bps plus 20 bps market impact on both selected and short benchmark legs
- Liquidity floor: entry amount >= 10,000,000
- Portfolio value: 1,000,000
- Max participation: 1% ADV
- Target gross exposure: 0.6

Output:

- `data/reports/beta_hedged_spread_public_risk_filter_round74_20260621_reb10_hedge1`

## Corrected Results

| Factor | Classification | Spread Total | Spread Sharpe | Overlap Sharpe | Max DD | Win Rate | Positive Folds | NW t-stat | Capacity Limited |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `risk_filter_bridge_equal_20` | weak | -14.17% | -0.6360 | -0.5160 | -14.31% | 46.23% | 1/11 | -3.8361 | 0 |
| `risk_filter_bridge_anti_obv_weighted_20` | weak | -12.91% | -0.6215 | -0.5186 | -13.62% | 45.80% | 0/11 | -3.8555 | 0 |
| `risk_filter_bridge_agreement_20` | weak | -13.92% | -0.7331 | -0.6100 | -15.00% | 44.22% | 1/11 | -4.5354 | 0 |

## Interpretation

The corrected fixed-ratio hedge rejects the spread translation layer.

Evidence:

- All three spreads are negative after applying the short benchmark leg costs correctly.
- Positive fold rate collapses to 0/11 or 1/11.
- Newey-West t-stat is strongly negative for every spread.
- Capacity is clean, so the rejection is not caused by position-size clipping.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Spread candidates: 0.

Rejected direction:

- Fixed 1.0 equal-weight benchmark hedge for the public risk-filter bridge family.

## Next Direction

Round75 should rerun the same corrected spread logic under harsher cost and impact stress to confirm the rejection is not a mild-cost edge case.

If the stress run also rejects the family, the public risk-filter bridge line should be hibernated and Round76 should rotate to a different public-method family.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
