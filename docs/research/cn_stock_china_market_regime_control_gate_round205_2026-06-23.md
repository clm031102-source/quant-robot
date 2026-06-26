# CN Stock China Market Regime Control Gate Round205

- Date: 2026-06-23
- Scope: CN stock pre-mining market-regime controls
- Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Why

The prior quality gate treated China-market regime controls as partial because some regime-linked alpha attempts failed and LPR coverage remained incomplete. That is the wrong framing for pre-mining controls. Regime variables should first be declared as PIT-safe stratification/control variables, not as standalone alpha.

## What Changed

- Added `configs/china_market_regime_control_policy_cn_stock.json`.
- Added `src/quant_robot/ops/china_market_regime_control_gate.py`.
- Added `scripts/run_china_market_regime_control_gate.py`.
- Added unit and CLI tests.

The gate requires each regime control to declare:

- dataset references,
- usable fields,
- blocked fields,
- `available_date_required=true`,
- `pit_join_required=true`,
- `standalone_alpha_claim_allowed=false`.

## Gate Result

Output: `data/reports/round205_china_market_regime_control_gate_20260623`

- Passes: true
- Implemented controls: 4
- Blocked alpha-claim controls: 0
- Blocked fields count: 2
- Blocked fields: `lpr_1y`, `lpr_5y`

## Interpretation

This upgrades the following controls as reusable regime-control infrastructure:

- `policy_liquidity_regime`
- `credit_cycle_proxy`
- `northbound_margin_turnover_temperature`
- `index_location_state`

This does not revive failed margin-credit or northbound alpha hypotheses. Those remain hibernated unless a new orthogonal hypothesis is pre-registered and passes residual, cost, capacity, and walk-forward gates.
