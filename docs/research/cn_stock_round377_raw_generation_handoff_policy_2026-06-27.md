# CN Stock Round377 - Raw Generation Handoff Policy

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: simulation-readiness process control for the 24h CN stock profit-factor sprint. Research-to-review only; no broker, account, order, or live-trading access.

## Why This Round

The project is close to a simulation-backtest handoff, but Round373-376 showed a dangerous failure mode: a raw-generated event stream can look economically similar while failing date-calendar parity against the frozen candidate evidence.

That is unacceptable for simulation handoff because the simulation stage must know exactly which event stream it is testing.

## Policy Added

`configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json` now includes `raw_generation_policy`:

- `parity_gate_required: true`;
- simulation event sources must remain frozen, replay-validated files until raw generation passes parity;
- raw-generated event sources require `event_calendar_parity_passed` status before they can replace frozen event files;
- Round367 generated low10 replacement stream is explicitly blocked as a simulation event source.

## Code Gate Added

`validate_simulation_shortlist_config` now blocks:

- missing or invalid `raw_generation_policy`;
- any simulation candidate whose `event_return_source.path` points to a blocked generated event source.

Unit coverage was added for both cases.

## Current Interpretation

This does not reject the five current simulation shortlist candidates. They continue to use frozen, replay-validated event files and passed the previous replay/schema checks.

It does reject one specific shortcut: using the Round367 raw-generated low10 stream as if it were an equivalent replacement for the official Round338/Round339 event stream.

## Next Work

Raw generation can resume only through one of these paths:

1. recover or regenerate the official trade-level evidence and reconstruct the 834-date period calendar;
2. build a new raw-generation pipeline that produces the same sorted date/return stream as the frozen reference within the parity gate;
3. if the rule cannot be reconstructed, keep the frozen event source for simulation and label raw-generated successor candidates as research-only until they have independent full validation.
