# CN Stock Round222 Financial PIT Post-Announcement Drift Matrix Label Smoke

Date: 2026-06-24

## Purpose

This artifact closes the pre-IC leakage gate for the Round222 financial PIT post-announcement drift family. It verifies that event-day reaction features are only used after they are observable and tradable, that forward labels start after the factor date, and that the 2026 final holdout is excluded by default.

## Command

```powershell
python scripts\run_financial_pit_post_announcement_drift_matrix_label_smoke.py --output-dir data\reports\financial_pit_post_announcement_drift_matrix_label_smoke_round222_20260624
```

## Result

- Passes: True
- Active candidates: 7
- Financial rows: 4,115
- Bar rows: 256,333
- Factor value rows: 28,802
- Label rows: 509,966
- Label aligned rows: 57,604
- Label coverage: 100.00%
- Alignment violations: 0
- Min signal date: 2015-04-16
- Max signal date: 2025-11-11
- Max factor date: 2025-11-12
- Max label date: 2025-12-23
- Horizons: 5, 20
- Execution lag: 1
- Unknown active formulas: 0
- Blockers: none

## Candidate Matrix Coverage

| Factor | Factor Rows | Label Rows | Coverage | Violations |
|---|---:|---:|---:|---:|
| `pead_event_reaction_continuation_1_20` | 4,115 | 8,230 | 100.00% | 0 |
| `pead_event_gap_underreaction_1_20` | 4,114 | 8,228 | 100.00% | 0 |
| `pead_volume_disagreement_drift_1_20` | 4,114 | 8,228 | 100.00% | 0 |
| `pead_late_announcer_risk_reversal_5_20` | 4,115 | 8,230 | 100.00% | 0 |
| `pead_positive_fundamental_change_low_reaction_20` | 4,115 | 8,230 | 100.00% | 0 |
| `pead_negative_surprise_reaction_avoidance_20` | 4,115 | 8,230 | 100.00% | 0 |
| `pead_reaction_quality_residual_composite_20` | 4,114 | 8,228 | 100.00% | 0 |

## Gate Decision

This is not profitability evidence. It does not compute IC, Sharpe, win rate, profit rate, total return, or drawdown.

Allowed next gate:

```text
round222_financial_pit_post_announcement_drift_residual_prescreen
```

Still blocked:

- Same-day announcement trading.
- Same-day event-reaction trading.
- IC, portfolio grids, or promotion before residual IC shape prescreen.
- Any 2026 final-holdout tuning before full validation clearance.

Safety boundary remains research-to-review only: no broker connection, no live account reads, no order placement, and no automatic live trading.
