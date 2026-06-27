# CN Stock Round415 - Signal Reconstruction Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round415 checks whether the current top-ranked candidate can be converted from an aggregate event-return stream into asset-level signal rows for the next paper-simulation stage.

Candidate:

`primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`

## Reusable Code Added

- `src/quant_robot/ops/simulation_shortlist_signal_reconstruction.py`
- `scripts/run_simulation_shortlist_signal_reconstruction.py`
- `tests/unit/test_simulation_shortlist_signal_reconstruction.py`
- `tests/unit/test_simulation_shortlist_signal_reconstruction_cli.py`

## Inputs

- Trades: `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`
- Event source: `data/reports/round407_24h_profit_sprint_alpha101_dragon_hot_self_risk_20260627/tilt_a101_open_100_self_roll21_sum_neg_half_events.csv`
- Dragon-Tiger source: `data/processed/round232_dragon_tiger_attention_reversal_20260624`
- Public factor source: `data/reports/round404_24h_profit_sprint_all_public_factor_source_for_dragon_hot_20260627/public_factor_values_for_shortlist.parquet`

Output:

`data/reports/round415_24h_profit_sprint_signal_reconstruction_20260627`

## Result

The asset-level reconstruction reproduces the historical event-return stream to numerical precision:

| Check | Value |
|---|---:|
| trade rows | 26,450 |
| event-matched trade rows | 26,306 |
| event rows | 834 |
| Dragon-Hot cash-filtered trades | 360 |
| Alpha101 bottom10 tilted trades | 2,420 |
| public factor missing share | 0.00% |
| max absolute return reconciliation diff | 2.83e-16 |
| sum absolute return reconciliation diff | 6.82e-14 |

## Paper-Readiness Gate

Status: blocked.

Blockers:

- `exit_timed_exposure_requires_entry_timed_rebuild`
- `event_decision_date_collapses_multiple_trade_decisions`
- `trade_pairs_missing_event_exposure`

Interpretation:

The current best candidate can be exactly reconstructed as an event-return stream, but it is not yet a clean paper-simulation signal. The existing wrapper exposure is keyed by the event/exit return date, and all 834 event rows have the return date after the recorded decision date. In addition, 161 event dates collapse multiple underlying trade decision dates into one event decision date.

This does not invalidate the research result, but it blocks direct promotion into paper simulation. A paper-ready version must recompute volatility target, ZZ500 regime, and self-risk exposure at the entry decision time, then rerun the full-sample/OOS/cost/beta gates.

## Decision

Do not hand the Round407 top candidate directly to paper simulation.

Round416 direction:

- rebuild the same Dragon-Hot plus Alpha101 entry selection at asset level;
- compute all exposure controls using only information available at each entry date;
- compare the entry-timed return stream against the exit-timed research stream;
- only keep the candidate if the entry-timed version still passes the 30% drawdown tolerance and has competitive annualized return/Sharpe after costs.
