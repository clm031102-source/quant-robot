# CN Stock Round692-694 Local Three-Round Review

Date: 2026-07-09

Machine/task: `office_desktop` / `factor_batch`

## Scope

This review covers the local factor-batch sequence after the financial-reporting-timeliness source gate was cleared, focusing on the last three completed mining attempts:

- Round692: PEAD gap-reversal source repair.
- Round693: statement working-capital pressure.
- Round694: statement capital-structure efficiency.

Round691 financial reporting timeliness also produced no promotable candidate locally and remains a related blocker for reentry. The review is intentionally source/direction focused; it does not promote any candidate and does not use the 2026 final holdout.

## Round Outcomes

| Round | Family | Key Result | Decision |
| --- | --- | --- | --- |
| 692 | `pead_gap_reversal_source_repair` | 5 candidates, 4 raw negative FDR-like clues, 0 neutral-gate passes, 0 research leads | Reject standalone source-repair continuation; no sign flip or grid expansion |
| 693 | `statement_working_capital_pressure` | 5 candidates, 10 tests, 0 multiple-testing leads, 0 neutral-gate passes, 0 research leads | Reject standalone working-capital pressure family |
| 694 | `statement_capital_structure_efficiency` | 5 candidates, 10 tests, 4 multiple-testing leads, 0 neutral-gate passes, 0 research leads | Reject standalone capital-structure efficiency family |

## Cross-Round Pattern

The recurring failure mode is not missing PIT mechanics. The startup gates, candidate-plan gates, formula/matrix smokes, label alignment, and local report-ignore policies worked. The recurring failure is factor materiality after neutralization.

Two variants are especially dangerous:

- Negative raw-direction FDR clues in Round692 and Round694 can invite sign flipping, but that would be post-result tuning.
- Positive industry-neutral ranks in some statement rows can coexist with weak or negative size/liquidity neutral ranks, so raw or single-neutral evidence is not enough.

## Hibernation Decisions

Do not continue these exact standalone families without a genuinely new source or mechanism and a fresh candidate-plan gate:

- `financial_reporting_timeliness`
- `pead_gap_reversal_source_repair`
- `statement_working_capital_pressure`
- `statement_capital_structure_efficiency`

Also keep the existing hibernations in force:

- direct profitability-quality formula tuning;
- realized statement profitability revision;
- statement event drift;
- old accounting-quality cash/accrual formula mutations;
- daily-basic valuation repair;
- public technical composites;
- old northbound accumulation or crowding/reversal;
- margin-credit factors;
- calendar seasonality.

## Allowed Next Direction

The next factor-batch attempt should not be another statement ratio mutation. The efficient next step is one of:

- a true source-quality audit for a not-yet-mined PIT feed before factor generation;
- a new external-expectation source with enough history and quota evidence;
- a non-statement event/context source with point-in-time available-date semantics and full neutralization planned.

If no such source is immediately available, pause formula generation and do source-readiness work instead of mining another adjacent statement transform.

## Safety Boundary

- No portfolio grid from Rounds 692-694.
- No promotion gate from Rounds 692-694.
- No sign flip after reading negative results.
- No lag, horizon, window, or formula tuning.
- No mixed-window harvesting.
- No 2026 final-holdout read for tuning.
- No broker connection, account read, order placement, or automatic live trading.

Generated `data/reports` evidence remains local and uncommitted.
