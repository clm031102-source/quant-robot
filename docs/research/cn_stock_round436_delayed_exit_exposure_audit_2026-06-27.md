# CN Stock Round436 Delayed-Exit Exposure Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round436 audited hidden industry, board, exchange, HS-connect, and delayed-exit-status exposure in the current delayed-exit handoff pack.

Inputs:

- full delayed-exit trade rows: `data/reports/round432_24h_profit_sprint_delayed_exit_return_repair_20260627/delayed_exit_trade_rows.csv`
- return column: `delayed_exit_weighted_return`
- decision/exposure date: `entry_date`

Outputs:

- full trade exposure audit: `data/reports/round436_24h_profit_sprint_delayed_exit_exposure_audit_20260627`
- active trade exposure audit: `data/reports/round436_24h_profit_sprint_delayed_exit_active_exposure_audit_20260627`

## Active Trade Exposure

The active-only audit filters to actually opened trades with `same_day_exit` or `delayed_exit` status.

| Metric | Value |
|---|---:|
| active rows | 20,367 |
| active target weight | 101.835 |
| active return contribution | 1.1245 |
| active entry dates | 529 |

Industry exposure is clean:

| Industry Metric | Value |
|---|---:|
| average group count | 27.81 |
| average HHI | 0.0483 |
| p95 top industry weight share | 16.67% |
| top industry absolute return contribution share | 6.72% |

Top active industry contributions:

| Industry | Weight Share | Return Contribution | Abs Contribution Share |
|---|---:|---:|---:|
| Securities | 6.88% | +0.0399 | 6.72% |
| Construction engineering | 6.68% | +0.0533 | 5.79% |
| Auto parts | 4.59% | +0.1071 | 4.51% |
| Home appliances | 3.80% | +0.0486 | 4.00% |
| Publishing | 3.80% | +0.0391 | 3.21% |

## Structural Concentration

The strategy is structurally a main-board, Shanghai-heavy, HS-connect-heavy strategy:

| Dimension | Top Group | Weight Share | Return Contribution | Abs Contribution Share |
|---|---|---:|---:|---:|
| stock market | Main board | 99.09% | +1.1033 | 98.26% |
| exchange | XSHG | 83.97% | +0.9030 | 79.50% |
| HS flag | H | 73.70% | +0.8110 | 67.61% |
| exit status | same-day exit | 98.97% | +1.1760 | 95.98% |

This is not automatically a blocker because it matches the tradeability repair: non-main-board and blocked-entry names mostly do not become active positions. But it must be disclosed in simulation as a boundary condition.

## Delayed Exit Read

Delayed exits are rare but negative:

| Exit Status | Weight Share | Return Contribution | Abs Contribution Share |
|---|---:|---:|---:|
| same-day exit | 98.97% | +1.1760 | 95.98% |
| delayed exit | 1.03% | -0.0515 | 4.02% |

Do not use `delayed_exit_status` as an entry filter because it is known only at the planned exit date. It remains an execution-risk diagnostic and simulation monitoring field.

## Decision

Do not add an industry cap overlay. Industry concentration is already below the configured exposure blockers.

Do disclose the following before simulation:

- the active candidate is overwhelmingly main-board;
- XSHG contributes most of the return;
- delayed exits are rare but costly;
- non-main-board signals are mostly removed by entry/tradeability rules and are not a live active sleeve.

No new factor or paper-ready candidate is promoted in Round436.
