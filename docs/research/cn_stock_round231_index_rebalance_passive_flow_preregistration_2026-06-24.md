# CN Stock Round231 Index Rebalance Passive Flow Preregistration - 2026-06-24

## Purpose

Round231 rotates away from the failed `liquidity_shock_recovery` family. The new family is `index_rebalance_passive_flow`, a point-in-time event/supply-demand mechanism based on Tushare `index_weight` snapshots.

This is intentionally different from the recent failed paths:

- not moneyflow;
- not OHLCV liquidity shock/reversal;
- not public trend/supertrend/Alpha101-style technical formulas;
- not direct profitability-quality formula tuning;
- not forecast/dividend/buyback-holder event reuse from the hibernated Round146-148 path.

## Hypothesis

Index additions, removals, and large weight changes can create short-term passive fund demand or supply pressure after the index-weight snapshot is publicly observable. The effect may be weak, crowded, or quickly reversed, so the first valid empirical step is PIT event IC plus industry/size neutralization. Portfolio conversion is explicitly blocked.

## Data And PIT Policy

- Source endpoint: Tushare `index_weight`.
- Required pre-audit: `index_rebalance_event_audit`.
- Event date: index-weight snapshot `trade_date`.
- Signal date: `available_date`, defined as the first open trade date strictly after the snapshot date.
- Same-day event trading: forbidden.
- Final holdout: not touched.
- Broker/account/order/live trading: forbidden.

## Pre-Registered Factors

| Factor | Direction | Formula Sketch | Rationale |
|---|---|---|---|
| `index_rebalance_add_pressure_1d` | higher is better | `current_weight if added else 0` | Inclusion may create passive demand. |
| `index_rebalance_remove_pressure_1d` | higher is better | `-prior_weight if removed else 0` | Removals are encoded as negative selling pressure. |
| `index_rebalance_weight_up_pressure_1d` | higher is better | `max(weight_delta, 0)` | Upweights may create incremental passive demand. |
| `index_rebalance_weight_down_pressure_1d` | higher is better | `min(weight_delta, 0)` | Downweights are encoded as negative selling pressure. |
| `index_rebalance_abs_flow_pressure_1d` | higher is better | `abs(weight_delta)` | Large absolute flow changes may proxy attention and liquidity demand. |

## Gate Rules

- Candidate count: 5 fixed names.
- Multiple testing count: every factor x horizon test.
- Allowed empirical step: PIT event IC plus industry/size neutralization.
- Portfolio grid allowed: false.
- Promotion allowed: false.
- A research lead only earns the right to reference de-dup or walk-forward preflight.
- If zero neutral research leads survive, Round232 must rotate away rather than tune thresholds or add index lists blindly.

## Expected Failure Modes

- Index events are clustered on rebalance dates, reducing independent observations.
- Events may be dominated by industry or size exposure.
- Effects may reverse after public announcement or be arbitraged away.
- CSI300/CSI500/CSI1000 coverage may be too narrow for robust cross-sectional inference.
- Large event-day returns could reflect event contamination rather than tradable forward alpha.

## Next Step

Run a long-cycle event audit and prescreen for broad A-share index baskets, starting with:

- `000300.SH` CSI 300;
- `000905.SH` CSI 500;
- `000852.SH` CSI 1000.

Output remains under ignored `data/reports/` paths until a lightweight report is written.
