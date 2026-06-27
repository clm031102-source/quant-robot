# CN Stock Round434 Calendar Overlay Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round434 tested whether simple entry-known calendar states can improve the current delayed-exit handoff pack. This is not a standalone calendar alpha search and not a free month-picking exercise. The fixed states were long-break windows, month starts/ends, quarter-end windows, and reporting-season months.

The only useful overlay was:

`zero_quarter_end5`: do not open new cohorts during the final 5 trading days of quarter-end months.

## Outputs

- State and variant audit: `data/reports/round434_24h_profit_sprint_calendar_state_overlay_audit_20260627`
- OOS split audit: `data/reports/round434_24h_profit_sprint_calendar_overlay_oos_20260627`
- Block audit: `data/reports/round434_24h_profit_sprint_calendar_overlay_block_audit_20260627`
- ZZ500 beta audit: `data/reports/round434_24h_profit_sprint_calendar_overlay_beta_20260627`

## Full-Sample Effect

| Candidate | Variant | Annualized | Total | Overlap Sharpe | Max DD | Best 3 Month Share |
|---|---|---:|---:|---:|---:|---:|
| 10 bps | baseline | 6.663% | +218.46% | 0.496 | -26.21% | 45.72% |
| 10 bps | zero quarter-end 5 | 6.400% | +204.62% | 0.546 | -23.20% | 39.61% |
| 20 bps | baseline | 6.060% | +187.60% | 0.456 | -28.07% | 49.87% |
| 20 bps | zero quarter-end 5 | 5.886% | +179.27% | 0.506 | -24.06% | 42.73% |
| 30 bps | baseline | 5.415% | +157.79% | 0.416 | -29.66% | 55.28% |
| 30 bps | zero quarter-end 5 | 5.284% | +152.08% | 0.465 | -25.61% | 47.14% |

The overlay consistently improves risk-adjusted quality and drawdown while sacrificing modest annualized return.

## OOS Check

| Candidate | Variant | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---|---:|---:|---:|---:|
| 10 bps | baseline | 10.043% | 0.831 | -19.30% | 90.00% |
| 10 bps | zero quarter-end 5 | 9.428% | 0.915 | -18.20% | 90.00% |
| 20 bps | baseline | 9.132% | 0.759 | -19.75% | 76.67% |
| 20 bps | zero quarter-end 5 | 8.668% | 0.845 | -18.62% | 90.00% |
| 30 bps | baseline | 8.197% | 0.684 | -20.28% | 76.67% |
| 30 bps | zero quarter-end 5 | 7.801% | 0.769 | -19.13% | 76.67% |

## Beta-Adjusted Check

| Candidate | Variant | ZZ500 Beta | Hedged Ann. | Hedged Overlap | Hedged Max DD | Alpha t |
|---|---|---:|---:|---:|---:|---:|
| 10 bps | baseline | 0.0480 | 7.485% | 0.792 | -14.14% | 4.36 |
| 10 bps | zero quarter-end 5 | 0.0423 | 7.273% | 0.869 | -12.34% | 4.46 |
| 20 bps | baseline | 0.0479 | 6.744% | 0.724 | -14.14% | 3.97 |
| 20 bps | zero quarter-end 5 | 0.0423 | 6.642% | 0.802 | -12.41% | 4.10 |
| 30 bps | baseline | 0.0471 | 5.952% | 0.651 | -14.36% | 3.57 |
| 30 bps | zero quarter-end 5 | 0.0415 | 5.901% | 0.726 | -12.56% | 3.71 |

## Decision

Add `zero_quarter_end5` as a paper-simulation risk overlay candidate, not as a replacement for the high-return default.

Use:

- default return-seeking lane: delayed-exit baseline;
- defensive simulation lane: delayed-exit plus no new quarter-end entries;
- heavy-cost stress lanes: compare baseline and quarter-end overlay side by side.

Remaining caveats:

- The overlay was discovered during the sprint, so it must be treated as a risk-control hypothesis and monitored for overfit.
- It reduces annualized return, so it should not replace the default if the objective is maximum total return under the user's 30% drawdown tolerance.
- It should be included in simulation as an alternative lane, not promoted as independent alpha.
