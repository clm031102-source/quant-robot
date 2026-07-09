# CN Stock Round691-694 Statement Source Rotation Closeout

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

This closeout records the local Round691-Round694 factor-screen evidence that was generated after Round690 cleared the financial reporting timeliness source gate. It makes the rejected statement-source rotations durable in Git so later factor batches do not repeat the same families under new names.

This document did not run new factor computation. It summarizes existing generated reports under `data/reports`, which remain out of Git.

No portfolio grid, walk-forward conversion, promotion gate, sign/window tuning, formula tuning, mixed-window harvesting, signal generation, or 2026 final-holdout read is claimed here.

## Evidence Sources

| Round | Family | Report |
| --- | --- | --- |
| 691 | Financial reporting timeliness | `data/reports/round691_financial_reporting_timeliness_residual_ic_shape_prescreen_20260709/accounting_quality_statement_residual_ic_shape_prescreen.json` |
| 692 | PEAD gap reversal source repair | `data/reports/round692_pead_gap_reversal_source_repair_residual_prescreen_20260709/financial_pit_post_announcement_gap_reversal_residual_prescreen.json` |
| 693 | Statement working-capital pressure | `data/reports/round693_statement_working_capital_pressure_residual_prescreen_20260709/accounting_quality_statement_residual_ic_shape_prescreen.json` |
| 694 | Statement capital-structure efficiency | `data/reports/round694_statement_capital_structure_efficiency_residual_prescreen_20260709/accounting_quality_statement_residual_ic_shape_prescreen.json` |

## Summary

| Round | Candidates | Tests | Factor Rows | Aligned Rows | FDR Leads | Neutral Passes | Research Leads | Promotion Allowed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 691 | 5 | 10 | 159,701 | 319,402 | 0 | 0 | 0 | 0 |
| 692 | 5 | 5 | 191,451 | 191,451 | 4 | 0 | 0 | 0 |
| 693 | 5 | 10 | 41,590 | 83,180 | 0 | 0 | 0 | 0 |
| 694 | 5 | 10 | 156,926 | 313,840 | 4 | 0 | 0 | 0 |

Data windows:

| Round | Bar Assets | Min Signal Date | Max Signal Date |
| --- | ---: | --- | --- |
| 691 | 959 | 2015-04-23 | 2025-11-03 |
| 692 | 959 | 2015-04-09 | 2025-11-12 |
| 693 | 959 | 2023-08-21 | 2025-11-03 |
| 694 | 959 | 2015-04-08 | 2025-12-18 |

Top diagnostics:

| Round | Top Factor | H | IC | ICIR | t | p | Q5-Q1 | FDR | IndNeuIC | SizeNeuIC | LiqNeuIC | Lead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 691 | `frt_late_reporter_risk_avoidance` | 5 | 0.0181 | 0.143 | 1.50 | 0.1343 | 0.0067 | no | 0.2985 | 0.0098 | 0.0137 | no |
| 692 | `stmt_pead_gap_overreaction_reversal_volume_confirmed_1_5` | 5 | -0.0303 | -0.176 | -2.99 | 0.0028 | -0.0053 | yes | 0.1452 | -0.0311 | -0.0285 | no |
| 693 | `swcp_free_cashflow_liability_buffer` | 20 | -0.0433 | -0.327 | -2.58 | 0.0100 | -0.0144 | no | 0.2141 | -0.0307 | -0.0424 | no |
| 694 | `scs_balanced_capital_structure_efficiency` | 20 | -0.0489 | -0.437 | -3.50 | 0.0005 | -0.0135 | yes | 0.1274 | -0.0302 | -0.0569 | no |

## Decisions

### Round691

Financial reporting timeliness is rejected for factor conversion after the broad-source replay. The best row did not clear FDR, IC materiality, ICIR, or size/liquidity neutral gates.

Do not continue with reporting-lag sign flips, reporting-lag window tuning, or portfolio grids.

### Round692

The old PEAD gap-reversal lead is rejected after source repair. Four rows remained statistically significant, but the repaired statement source inverted the expected direction: IC, ICIR, quantile spread, size-neutral IC, and liquidity-neutral IC were all negative for the top variants.

Do not flip the direction after reading this result, and do not revive the Round223/Round225 gap-reversal family without a genuinely new orthogonal repair.

### Round693

Statement working-capital pressure is rejected. It produced zero FDR leads, zero neutral passes, and zero research leads. The apparent top rows were negative and failed quantile shape plus style/liquidity gates.

Do not tune working-capital component weights, pressure windows, or balance-sheet sub-formulas.

### Round694

Statement capital-structure efficiency is rejected. Four tests were FDR-significant, but in the wrong direction and with negative quantile spread plus failed size/liquidity neutral gates.

Do not use these negative diagnostics as a direction-flip invitation. The family is closed unless a future plan introduces a new external expectation or event mechanism rather than another adjacent statement ratio.

## Next Direction

Rotate away from adjacent realized-statement ratio families and PEAD source-repair variants. The valid next work is either:

- a genuinely new PIT-safe source mechanism with a preregistered candidate-plan gate; or
- source accumulation/audit work that improves an orthogonal feed without making alpha claims.

Round695-Round700 already followed that rotation through LPR/HK-hold source audit and analyst-report source extension. Those later rounds remain non-promotable as separately documented.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No final-holdout read.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
