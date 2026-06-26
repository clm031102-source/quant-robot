# CN Stock Round146-148 Three-Round Review

Date: 2026-06-22

Machine/task: office_desktop / factor_validation

Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Scope: CN A-share stock cross-sectional alpha research only.

## Rounds Reviewed

Round146: event-factor preregistration.

- Objective: add point-in-time event hypotheses instead of continuing the previous failed same-family sweeps.
- Output: 5 available event candidates.
- Decision: no portfolio grid; event factors required PIT/IC prescreen first.

Round147: event-factor PIT/IC prescreen.

- Candidates: 5
- Factor rows: 216,112
- Aligned rows: 423,204
- Tests: 10
- Research leads: 1
- Promotion candidates: 0
- Lead: `event_dividend_cash_yield_announced_1y`, horizon 20
- Lead metrics: IC 0.1082, ICIR 0.629, t-stat 6.62, IC positive rate 75.7%, Q5-Q1 2.23%, industry-neutral IC 0.278, size-neutral IC 0.100
- Decision: useful research lead only; de-dup and residual audit required before portfolio conversion.

Round148: event dividend public-reference/exposure de-dup.

- Lead rows: 9,934
- Raw IC observations: 90
- Raw mean IC: 0.0834
- Raw ICIR: 0.475
- Residual IC observations: 72
- Residual mean IC: 0.0241
- Residual ICIR: 0.141
- Public exposure: high to `daily_basic_dv_ratio`, moderate to `daily_basic_dv_ttm` and `daily_basic_inv_pe_ttm`
- Residual yearly failures: 2019, 2021, 2022
- Promotion candidates: 0
- Portfolio conversion candidates: 0

## Three-Round Audit

The direction change at Round146 was correct. It stopped the previous habit of pushing weak same-family variants and moved to event data with an explicit point-in-time rule.

The Round147 result was useful but not promotable. It found one signal worth auditing, not one tradable factor.

The Round148 audit prevents a false promotion. The raw dividend-event signal is partly real, but the long-cycle residual component is too weak and unstable after public dividend/value exposure neutralization. This is exactly the kind of result the new process is supposed to catch before money is spent on portfolio grids.

## Rejected Directions

Reject:

- event-dividend direct portfolio grid from Round147 IC
- event-dividend promotion based on raw IC only
- event-dividend residual promotion from 2024-2025-only coverage
- more event-dividend parameter variants before public-reference de-dup clears
- event-factor promotion from unsharded Tushare endpoint pulls that can hit row caps

## Provider/Data Issue

The Tushare dividend endpoint showed a row-cap/coverage risk during the Round148 audit. Annual `end_date` pulls often returned exactly 2,000 rows, and one annual period returned 0 rows during a live smoke probe.

This is now a process rule:

- future event-factor work must first use sharded and cached endpoint ingestion;
- event endpoint coverage diagnostics must report row caps, missing periods, min/max announcement dates, and endpoint errors;
- no event factor can be promoted from a capped or silent-skip event pull.

## Decision

The event-dividend line is not worth more immediate factor-mining budget.

Round149 should rotate away from event-dividend and avoid another narrow parameter sweep. A future event-factor revisit is allowed only as an ingestion/coverage repair task first, not as alpha promotion work.

Next direction:

`round149_event_factor_family_rotation_after_dedup_failure`

## Useful Outcome

The most useful achievement of these three rounds is not a profitable factor. It is a better kill switch:

1. pre-register event hypotheses;
2. run PIT/IC before portfolio grids;
3. de-duplicate against public daily-basic references;
4. residualize before claiming independence;
5. rotate after residual instability instead of tuning more parameters.

This lowers future waste. The current event-dividend factor is rejected for promotion.
