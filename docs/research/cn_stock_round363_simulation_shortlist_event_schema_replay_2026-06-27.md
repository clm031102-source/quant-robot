# CN Stock Round363 Simulation Shortlist Event-Schema Replay

Date: 2026-06-27

Machine/task: `office_desktop` / `factor_validation`

Safety boundary: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Purpose

Round361 replayed the packaged event-return streams against the shortlist config evidence. Round363 adds a stricter handoff gate: simulation candidates now also need coherent event structure, not just matching headline metrics.

The new replay checks:

- structured candidates have `decision_date`;
- volatility-target or external-regime candidates have `final_exposure`;
- external-regime candidates have `regime_guard_exposure` or `final_exposure`;
- `decision_date` is not after the event return date;
- declared `risk_off_exposure_multiplier` matches the event file when the file declares `riskoff_multiplier`;
- `final_exposure` stays in a sane nonnegative range.

## Command

```powershell
.venv\Scripts\python.exe scripts\run_simulation_shortlist_replay.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round363_24h_profit_sprint_simulation_shortlist_event_schema_replay_20260627 --metric-tolerance 0.005
```

## Result

Status: `passed`

Blockers: none

Candidates replayed: 5 of 5

All five candidates still match config evidence within tolerance and now pass event-schema checks.

| Candidate | Return column | Expected multiplier | Observed multiplier | Exposure min | Exposure max | Blockers |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `primary_high_return` | `period_return` | n/a | n/a | 0.4468 | 1.0000 | none |
| `primary_defensive_zz500` | `period_return` | 0.50 | 0.50 | 0.2533 | 1.0000 | none |
| `primary_balanced_zz500_75` | `period_return` | 0.75 | 0.75 | 0.3800 | 1.0000 | none |
| `safer_defensive_zz500` | `overlay_return` | 0.50 | n/a | 0.2445 | 1.0000 | none |
| `primary_ps_filtered_defensive_zz500` | `period_return_variant` | 0.50 | 0.50 | 0.2533 | 1.0000 | none |

## Interpretation

This is not a final promotion signal and does not unseal the 2026 holdout. It does make the current simulation handoff safer: a copied metric table, wrong return column, missing event-time column, or mismatched regime multiplier should now be caught before simulation packaging.

Remaining gap: this still starts from generated event CSV files. The next engineering target is a raw-input-to-event regeneration path for the retained lanes.
