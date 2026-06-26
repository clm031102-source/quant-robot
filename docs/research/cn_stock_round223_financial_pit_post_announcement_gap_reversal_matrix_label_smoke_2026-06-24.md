# CN Stock Round223 Financial PIT Post-Announcement Gap Reversal Matrix Label Smoke

Date: 2026-06-24

## Purpose

Round222 found the registered gap-underreaction sign was wrong. This artifact verifies the freshly pre-registered inverse event-gap reversal formulas before any IC or portfolio work.

## Command

```powershell
python scripts\run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke.py --output-dir data\reports\financial_pit_post_announcement_gap_reversal_matrix_label_smoke_round223_20260624
```

## Result

- Passes: True
- Active candidates: 5
- Unknown formulas: 0
- Financial rows: 4,115
- Bar rows: 256,333
- Factor value rows: 20,570
- Label aligned rows: 20,570
- Label coverage: 100.00%
- Alignment violations: 0
- Max signal date: 2025-11-11
- Max factor date: 2025-11-12
- Max label date: 2025-12-23
- Horizon: 5
- Execution lag: 1
- Next allowed gate: `round223_financial_pit_post_announcement_gap_reversal_residual_prescreen`

## Candidate Coverage

| Factor | Factor Rows | Label Rows | Coverage | Violations |
|---|---:|---:|---:|---:|
| `pead_gap_overreaction_reversal_1_5` | 4,114 | 4,114 | 100.00% | 0 |
| `pead_gap_overreaction_reversal_volume_confirmed_1_5` | 4,114 | 4,114 | 100.00% | 0 |
| `pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` | 4,114 | 4,114 | 100.00% | 0 |
| `pead_gap_overreaction_reversal_size_neutral_candidate_1_5` | 4,114 | 4,114 | 100.00% | 0 |
| `pead_gap_overreaction_reversal_quality_conditioned_1_5` | 4,114 | 4,114 | 100.00% | 0 |

## Gate Decision

This is not profitability evidence. It only proves the formulas and labels are usable without same-day event leakage.

Allowed next action:

```text
round223_financial_pit_post_announcement_gap_reversal_residual_prescreen
```

Still blocked: portfolio grids, Sharpe ranking, profit-rate claims, final-holdout tuning, and promotion.
