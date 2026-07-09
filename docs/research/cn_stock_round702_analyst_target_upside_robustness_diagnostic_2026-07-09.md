# CN Stock Round702 Analyst Target Upside Robustness Diagnostic

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round702 did a no-provider, local-only robustness diagnostic on the Round701 analyst-report revision prescreen outputs. The goal was to determine whether the improved January-June 2024 result for `analyst_target_upside_60` was broad enough to justify continued source accumulation, or whether it was mainly a June-window artifact.

This diagnostic only read frozen Round700/Round701 CSV and JSON outputs. It did not run new Tushare provider requests, factor formula changes, sign/window tuning, portfolio grids, walk-forward conversion, signal generation, promotion gates, mixed-window harvesting, or 2026 final-holdout reads.

## Startup And Data Control

Fresh startup evidence:

| Check | Result |
| --- | --- |
| Current branch | `codex/factor-batch-cn-stock-source-readiness-round695-20260709` |
| Worktree before work | clean |
| Quant PM startup gate | `ready`, blockers `[]`, primary market `CN_ETF` |
| CN stock factor-mining startup gate | `cleared`, startup gate cleared `true` |
| CN stock data manifest | `review_required`, blockers `[]` |
| Manifest warnings | `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars` |

Data manifest context:

| Metric | Value |
| --- | ---: |
| Bar rows | 15,930,072 |
| Bar symbols | 5,774 |
| Bar date range | 2015-01-05 to 2026-06-15 |
| Moneyflow rows | 14,702,368 |
| Moneyflow symbols | 5,648 |
| Missing adjusted-close rows | 0 |
| Zero amount rows | 0 |
| Zero volume rows | 0 |

Input reports:

- `data/reports/round700_analyst_report_revision_jan_may_prescreen_20260709/analyst_report_revision_prescreen_results.csv`
- `data/reports/round700_analyst_report_revision_jan_may_prescreen_20260709/analyst_report_revision_prescreen_ic_observations.csv`
- `data/reports/round701_analyst_report_revision_jan_jun_prescreen_20260709/analyst_report_revision_prescreen_results.csv`
- `data/reports/round701_analyst_report_revision_jan_jun_prescreen_20260709/analyst_report_revision_prescreen_ic_observations.csv`
- `data/reports/round701_analyst_report_revision_jan_jun_prescreen_20260709/analyst_report_revision_prescreen_neutral_observations.csv`

## Round701 Result Snapshot

Round701 still had zero research leads and zero promotion-allowed candidates, but four of eight tests passed FDR after adding June 2024 reports.

| Factor | H | IC | ICIR | t | FDR | SizeNeuIC | Size t | Lead |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `analyst_target_upside_60` | 5 | 0.1511 | 0.577 | 3.74 | yes | 0.1146 | 2.91 | no |
| `analyst_target_upside_60` | 20 | 0.0860 | 0.425 | 2.75 | yes | 0.0521 | 1.77 | no |
| `analyst_revision_target_composite_90` | 20 | 0.0510 | 0.379 | 2.51 | yes | 0.0425 | 2.06 | no |
| `analyst_revision_target_composite_90` | 5 | 0.0432 | 0.350 | 2.32 | yes | 0.0251 | 1.32 | no |

Main blocker: `ic_year_count=1` and `year_coverage_pass_count=0`.

## Jan-May To Jan-Jun Increment

The stronger Round701 statistics came from the newly added June-cache observations. That is useful source evidence, but it is also a clear robustness warning.

| Factor | H | Jan-May n | Jan-May IC | Jan-Jun n | Jan-Jun IC | Added n | Added mean IC | FDR Jan-May | FDR Jan-Jun | Size t Jan-May | Size t Jan-Jun |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |
| `analyst_target_upside_60` | 5 | 28 | 0.0940 | 42 | 0.1511 | 14 | 0.2653 | false | true | 1.14 | 2.91 |
| `analyst_target_upside_60` | 20 | 28 | 0.0477 | 42 | 0.0860 | 14 | 0.1625 | false | true | 0.38 | 1.77 |
| `analyst_revision_target_composite_90` | 20 | 29 | 0.0367 | 44 | 0.0510 | 15 | 0.0787 | false | true | 1.06 | 2.06 |
| `analyst_revision_target_composite_90` | 5 | 29 | 0.0290 | 44 | 0.0432 | 15 | 0.0708 | false | true | 0.05 | 1.32 |

New observations versus Round700 were dated 2024-06-11/12 through 2024-07-01 depending on factor. For `analyst_target_upside_60`, the added rows had average cross-section only 64.4, so the strong added IC should be treated as a small-cohort source-accumulation clue, not a conversion trigger.

## Signal-Month Stability

For the current top row, `analyst_target_upside_60` horizon 5:

| Signal month | n | Mean IC | Positive rate | Avg cross-section |
| --- | ---: | ---: | ---: | ---: |
| 2024-01 | 3 | 0.2666 | 100.0% | 186.3 |
| 2024-02 | 10 | -0.0777 | 40.0% | 101.3 |
| 2024-03 | 2 | 0.1746 | 100.0% | 97.5 |
| 2024-04 | 2 | 0.3887 | 100.0% | 576.5 |
| 2024-05 | 10 | 0.1466 | 80.0% | 140.7 |
| 2024-06 | 14 | 0.2578 | 85.7% | 60.8 |
| 2024-07 | 1 | 0.1213 | 100.0% | 122.0 |

Neutralized signal-month check for the same row:

| Signal month | n | Mean size-neutral IC | Mean industry-neutral IC |
| --- | ---: | ---: | ---: |
| 2024-01 | 3 | 0.1942 | 0.5729 |
| 2024-02 | 10 | -0.0988 | 0.3711 |
| 2024-03 | 2 | 0.2085 | 0.3202 |
| 2024-04 | 2 | 0.3915 | 0.5497 |
| 2024-05 | 10 | 0.0817 | 0.3965 |
| 2024-06 | 14 | 0.2331 | 0.4116 |
| 2024-07 | 1 | -0.0624 | 0.6690 |

February is the main adverse month. June is the main positive increment. This pattern is plausible for an analyst-target-upside signal, but the current sample is too short to separate structural effect from one-month noise.

## Leave-One-Signal-Month-Out

`analyst_target_upside_60` horizon 5 remains positive when any single signal month is excluded, but the strength falls sharply when June is removed.

| Excluded signal month | Kept n | Mean IC | Positive rate |
| --- | ---: | ---: | ---: |
| 2024-01 | 39 | 0.1422 | 74.4% |
| 2024-02 | 32 | 0.2226 | 87.5% |
| 2024-03 | 40 | 0.1499 | 75.0% |
| 2024-04 | 40 | 0.1392 | 75.0% |
| 2024-05 | 32 | 0.1525 | 75.0% |
| 2024-06 | 28 | 0.0977 | 71.4% |
| 2024-07 | 41 | 0.1518 | 75.6% |

For horizon 20, removing June leaves mean IC only 0.0357, which is below the full-sample 0.0860 and does not support conversion.

## Decision

Continue analyst-report revision as a controlled source-accumulation line, with `analyst_target_upside_60` horizon 5 as the priority diagnostic row.

Do not promote it to a research lead yet. The evidence improved after June and survives a simple leave-one-month-out check at horizon 5, but it is still single-year evidence, has one clearly negative month, and depends materially on a small added June cohort. This is exactly the zone where multiple-testing and regime-blindness can trick a researcher into overclaiming.

Allowed next action after `report_rc` quota resets:

- cache the next monthly analyst-report window under quota preflight;
- rerun the same frozen prescreen;
- update this robustness diagnostic with another out-of-time month;
- keep the family active only if FDR, size-neutral evidence, and year/month coverage improve without formula changes.

Blocked actions:

- no portfolio grid;
- no walk-forward conversion;
- no target-upside formula tuning;
- no sign/window tuning;
- no threshold relaxation;
- no promotion gate;
- no signal generation;
- no 2026 final-holdout read;
- no same-day extra provider request after Round701 exhausted the local daily budget.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
