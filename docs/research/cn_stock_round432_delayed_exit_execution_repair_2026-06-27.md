# CN Stock Round432 Delayed-Exit Execution Repair

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round432 replaces the Round430 `roundtrip_cash_proxy` diagnostic with a more causal execution repair.

If a planned exit date is not sellable, the repair delays the exit to the first sellable date within 10 calendar days and recomputes the trade return from entry price to that delayed exit price. Entry-blocked and unresolved-exit trades keep a zero return at the planned exit date so zero events are not dropped from the event calendar.

## Reusable Code Added

- `src/quant_robot/ops/shortlist_delayed_exit_return_repair.py`
- `scripts/run_shortlist_delayed_exit_return_repair.py`
- `tests/unit/test_shortlist_delayed_exit_return_repair.py`
- `tests/unit/test_shortlist_delayed_exit_return_repair_cli.py`

Important bug fixed during this round:

The first delayed-exit implementation left `delayed_exit_date` blank for zero-return entry-blocked or unresolved trades. That caused downstream cohort grouping to drop zero-return rows, artificially increasing annualized return and win rate. The fix preserves the planned exit date for zero-return rows.

## Inputs

Trade source:

`data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`

Bars:

- `data/processed/cn_stock_long_history_2015_202306/processed/bars`
- `data/processed/office_desktop_20260616_combined_research/processed/bars`

Tradeability masks:

`data/processed/round198_tradeability_mask_cache_2015_2025_20260623/processed/tradeability_masks`

Repair output:

`data/reports/round432_24h_profit_sprint_delayed_exit_return_repair_20260627`

Candidate output:

`data/reports/round432_24h_profit_sprint_delayed_exit_m150_20260627`

## Execution Repair Summary

| Metric | Value |
|---|---:|
| source trades | 26,450 |
| same-day sellable exits | 20,158 |
| delayed exits | 209 |
| entry-blocked zero-return trades | 6,068 |
| unresolved exits within 10 days | 15 |
| max observed exit delay | 10 days |
| missing-price trades | 0 |

## Candidate Metrics

| Candidate | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Event Count |
|---|---:|---:|---:|---:|---:|---:|---:|
| Round425 default | 5.759% | +163.48% | 0.863 | 0.466 | -29.18% | 40.71% | 872 |
| Round430 roundtrip m150 | 5.832% | +166.65% | 0.888 | 0.486 | -25.98% | 39.79% | 872 |
| Round432 delayed-exit m150 | 6.663% | +218.46% | 0.968 | 0.496 | -26.21% | 41.33% | 905 |

The delayed-exit candidate is stronger than the default after preserving zero-return events.

## OOS

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| Round425 default | 8.533% | 0.881 | -20.94% | 90.00% |
| Round430 roundtrip m150 | 8.369% | 0.873 | -19.46% | 90.00% |
| Round432 delayed-exit m150 | 10.043% | 0.831 | -19.30% | 90.00% |

Delayed-exit m150 has the best OOS annualized return and best worst OOS drawdown, but a lower mean OOS overlap Sharpe than the default.

## Beta

| Candidate | ZZ500 Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged Max DD | Alpha t |
|---|---:|---:|---:|---:|---:|---:|
| delayed-exit m150 | 0.0480 | 0.271 | 7.485% | 0.792 | -14.14% | 4.36 |
| roundtrip m150 | 0.0460 | 0.278 | 6.264% | 0.778 | -13.55% | 3.93 |
| default | 0.0474 | 0.285 | 6.234% | 0.752 | -15.10% | 3.87 |

The delayed-exit candidate improves beta-hedged annualized return, beta-hedged overlap, and alpha t-stat.

## Extreme And Block Checks

Extreme profile:

`data/reports/round432_24h_profit_sprint_delayed_exit_extreme_profile_20260627`

| Metric | Value |
|---|---:|
| contributing active trades | 20,117 |
| contributing extreme trades | 112 |
| extreme trade rate | 0.557% |
| extreme contribution sum | +41.70 pp |
| max contributing abs gross return | 255.55% |
| negative extreme count | 3 |

Block audit:

`data/reports/round432_24h_profit_sprint_delayed_exit_block_audit_20260627`

Result:

- blockers: none;
- leave-one-year min annualized return: 5.00%;
- leave-one-year min overlap Sharpe: 0.425;
- best three months log share: 45.72%;
- worst year: 2018 at -15.63%.

## Decision

Promote `round432_delayed_exit_m150` to the current best research-to-paper candidate.

This is not final live approval. It is the strongest simulation-preparation candidate found so far because it:

- fixes the exit-tradeability issue causally rather than by future entry filtering;
- improves full-sample return, drawdown, Sharpe, and overlap Sharpe versus the default;
- improves OOS annualized return and worst OOS drawdown;
- improves beta-hedged annualized return, beta-hedged overlap, and alpha t-stat;
- passes the block audit without dropping zero-return events.

Remaining caveat:

Mean OOS overlap Sharpe is lower than the default. Before simulation handoff, this candidate needs heavy-cost stress and a final replay/handoff gate.
