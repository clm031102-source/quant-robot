# CN Stock Round223 Financial PIT Post-Announcement Gap Reversal Residual Prescreen

Date: 2026-06-24

## Purpose

Round222 rejected the original post-announcement gap-underreaction direction but exposed a strong negative IC for the gap signal. Round223 pre-registered the inverse event-gap reversal hypothesis and screened it across the long 2015-2025 sample with PIT event-date alignment, multiple-testing control, quantile shape, industry/size/liquidity neutral checks, and static profitability reference de-duplication.

## Commands

```powershell
python scripts\run_financial_pit_post_announcement_gap_reversal_preregistration.py --output-dir data\reports\financial_pit_post_announcement_gap_reversal_preregistration_round223_20260624
python scripts\run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke.py --output-dir data\reports\financial_pit_post_announcement_gap_reversal_matrix_label_smoke_round223_20260624
python scripts\run_financial_pit_post_announcement_gap_reversal_residual_prescreen.py --output-dir data\reports\financial_pit_post_announcement_gap_reversal_residual_prescreen_round223_20260624 --allow-not-ready
```

## Result

- Passes: True as a research screen.
- Candidates: 5
- Tests: 5
- Factor rows: 20,570
- Aligned label rows: 20,570
- IC observation dates: 30
- Multiple-testing lead count: 5
- Neutral gate pass count: 5
- Reference de-dup pass count: 5
- Research lead count: 5
- Promotion allowed candidates: 0
- Max factor date: 2025-11-12
- Max label date: 2025-12-23

## Ranked Leads

| Factor | H | IC | ICIR | t | Pos IC | QSpread | Mono | IndNeuIC | SizeNeuIC | LiqNeuIC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` | 5 | 0.1383 | 0.731 | 4.01 | 80.0% | 0.0151 | 0.800 | 0.1973 | 0.1183 | 0.1370 |
| `pead_gap_overreaction_reversal_1_5` | 5 | 0.1240 | 0.626 | 3.43 | 73.3% | 0.0117 | 0.900 | 0.1992 | 0.0982 | 0.1129 |
| `pead_gap_overreaction_reversal_size_neutral_candidate_1_5` | 5 | 0.1219 | 0.623 | 3.41 | 70.0% | 0.0104 | 0.800 | 0.2034 | 0.1013 | 0.1141 |
| `pead_gap_overreaction_reversal_volume_confirmed_1_5` | 5 | 0.1069 | 0.510 | 2.79 | 70.0% | 0.0054 | 0.800 | 0.1695 | 0.0848 | 0.0981 |
| `pead_gap_overreaction_reversal_quality_conditioned_1_5` | 5 | 0.0654 | 0.417 | 2.28 | 63.3% | 0.0086 | 1.000 | 0.1918 | 0.0571 | 0.0564 |

## Audit Notes

- These are research leads, not tradable factors.
- The earlier duplicate issue between the base and size-neutral candidate was fixed before the final rerun; the size-neutral candidate now includes a small event-amount-rank penalty.
- All promotion remains blocked by required walk-forward, transaction-cost, capacity, regime, and final-holdout gates.
- No 2026 final-holdout tuning was used.

## Gate Decision

Allowed next action:

```text
round224_financial_pit_post_announcement_gap_reversal_reference_dedup_walk_forward_preflight
```

Blocked until that gate passes: portfolio grids, Sharpe/win-rate/profit-rate claims, paper-ready labels, and promotion.
