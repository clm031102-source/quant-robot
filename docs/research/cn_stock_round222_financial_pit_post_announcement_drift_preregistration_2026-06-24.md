# CN Stock Round222 Financial PIT Post-Announcement Drift Preregistration

Date: 2026-06-24

Scope: CN A-share stock cross-sectional alpha research. This is preregistration and coverage evidence only. It is not ETF rotation, not a portfolio backtest, not a promotion memo, and not live trading.

## Command

```powershell
python scripts\run_financial_pit_post_announcement_drift_preregistration.py --output-dir data\reports\financial_pit_post_announcement_drift_preregistration_round222_20260624
```

Local output:

`data/reports/financial_pit_post_announcement_drift_preregistration_round222_20260624/`

## Result

The Round222 financial PIT post-announcement drift preregistration cleared the coverage gate:

| Metric | Value |
|---|---:|
| Financial rows | 4,115 |
| Financial assets | 100 |
| Bar rows | 256,333 |
| Bar assets | 100 |
| Candidate ideas | 7 |
| Unique signal dates | 579 |
| Event reaction available rows | 4,115 |
| Event reaction coverage | 100.00% |
| Signal date missing rows | 0 |
| Signal date on/before announcement rows | 0 |
| Reaction available date missing rows | 0 |
| Reaction available on/before announcement rows | 0 |
| Min signal date | 2015-04-16 |
| Max signal date | 2025-11-11 |
| Min reaction available date | 2015-04-17 |
| Max reaction available date | 2025-11-12 |
| Blockers | 0 |

Important holdout correction:

- The first real run exposed that the filtered financial root contains 2026 rows.
- The preregistration tool now defaults to `analysis_end_date=2025-12-31` and `include_final_holdout=false`.
- Regression coverage confirms final-holdout dates are excluded by default.
- The accepted real run does not read 2026 signal/reaction dates.

## Pre-Registered Candidate Ideas

- `pead_event_reaction_continuation_1_20`
- `pead_event_gap_underreaction_1_20`
- `pead_volume_disagreement_drift_1_20`
- `pead_late_announcer_risk_reversal_5_20`
- `pead_positive_fundamental_change_low_reaction_20`
- `pead_negative_surprise_reaction_avoidance_20`
- `pead_reaction_quality_residual_composite_20`

## Interpretation

This round proves only that the event timing and reaction-availability data are usable for a controlled matrix/label smoke:

- `signal_date` is after `ann_date`.
- event-day reaction is only allowed from a later tradable `reaction_available_date`;
- 2026 final holdout is excluded by default;
- no portfolio grid, Sharpe, annual return, profit rate, win rate, or promotion claim is allowed from this artifact.

Next allowed gate:

`round222_financial_pit_post_announcement_drift_matrix_label_smoke`

## Safety

Research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.
