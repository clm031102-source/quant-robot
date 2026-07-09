# CN Stock Round691 Financial Reporting Timeliness Prescreen

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709`

Scope: run the first specialized PIT residual IC shape prescreen for the five Round691 pre-registered `financial_reporting_timeliness` candidates after the candidate plan gate cleared. This round used fixed 5D and 20D horizons only. It did not run portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, live-trading work, broker reads, account reads, order placement, or 2026 final-holdout reads.

## Startup And Gate Evidence

| Check | Result |
| --- | --- |
| Startup context | `office_desktop` / `factor_batch`, current branch matched |
| Quant PM startup gate | `ready`, blockers `[]`, primary market `CN_ETF` |
| Factor mining startup gate | `cleared`, blockers `[]` |
| CN stock data manifest | `review_required`, blockers `[]` |
| Manifest warnings | `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars` |
| Candidate plan gate | `research_ready`, blockers `[]`, research screen allowed true |
| Candidate plan controls | 9 / 9 complete, 0 blocked |

Manifest warnings are carried forward as audit context. They are not alpha evidence, and no result below should be interpreted as portfolio-ready.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py --statement-root data\processed --factor-mode financial_reporting_timeliness --horizon 5 --horizon 20 --output-dir data\reports\round691_financial_reporting_timeliness_residual_ic_shape_prescreen_20260709 --allow-not-ready
```

The command emitted repeated numpy `invalid value encountered in divide` warnings from zero-variance correlation slices during neutral IC calculations. The run completed and wrote the report with blockers `[]`.

## Prescreen Result

| Metric | Value |
| --- | ---: |
| Passes | true |
| Blockers | `[]` |
| Candidates | 5 |
| Factor names with rows | 5 |
| Factor rows | 159,701 |
| Label rows | 4,653,662 |
| Aligned rows | 319,402 |
| Horizon tests | 10 |
| FDR-significant tests | 0 |
| Neutral-gate pass tests | 0 |
| Research leads | 0 |
| Promotion allowed candidates | 0 |

Data window:

| Field | Value |
| --- | --- |
| Bar dates | 2015-01-05 to 2025-12-31 |
| Signal dates | 2015-04-23 to 2025-11-03 |
| Label dates | 2015-01-05 to 2025-12-23 |
| Bar assets | 959 |

## PIT Alignment

| Check | Value |
| --- | ---: |
| Factor rows checked | 159,701 |
| `signal_date <= ann_date` rows | 0 |
| `date != signal_date` rows | 0 |
| Missing alignment-date rows | 0 |
| PIT alignment passes | true |

The factor values are dated on the first tradable signal date strictly after `ann_date`; period-end-only availability remains blocked.

## Candidate Coverage

| Candidate | Factor rows | Assets | Signal range |
| --- | ---: | ---: | --- |
| `frt_reporting_lag_short` | 32,982 | 958 | 2015-04-23 to 2025-11-03 |
| `frt_reporting_lag_improvement_4q` | 30,182 | 956 | 2016-04-11 to 2025-11-03 |
| `frt_reporting_lag_stability_8q` | 30,830 | 956 | 2016-03-28 to 2025-11-03 |
| `frt_early_report_quality_combo` | 32,725 | 957 | 2015-04-23 to 2025-11-03 |
| `frt_late_reporter_risk_avoidance` | 32,982 | 958 | 2015-04-23 to 2025-11-03 |

## Top IC Shape Results

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | Lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `frt_late_reporter_risk_avoidance` | 5 | 0.0181 | 0.143 | 1.50 | 52.7% | 0.0067 | 0.2985 | no |
| `frt_reporting_lag_short` | 5 | -0.0100 | -0.072 | -0.96 | 46.6% | 0.0013 | 0.2441 | no |
| `frt_early_report_quality_combo` | 20 | 0.0077 | 0.061 | 1.03 | 52.8% | 0.0022 | 0.1132 | no |
| `frt_early_report_quality_combo` | 5 | -0.0070 | -0.055 | -0.93 | 48.9% | 0.0010 | 0.0835 | no |
| `frt_reporting_lag_short` | 20 | -0.0061 | -0.049 | -0.65 | 47.8% | 0.0059 | 0.2615 | no |

None of the ten candidate x horizon tests passed FDR plus neutral-gate requirements. This is rejection evidence for the first standalone Round691 timeliness formulation, not a profitability or portfolio result.

## Decision

Do not promote any Round691 `financial_reporting_timeliness` candidate. Do not run portfolio grids, walk-forward, cost/capacity, regime promotion, or final-holdout reads from this result.

Next direction:

```text
round692_rotate_or_repair_financial_reporting_timeliness_after_residual_ic_shape_failure
```

Reasonable next research action is a pre-registered repair or rotation, such as a stricter event-window/data-quality repair, a different expectation-revision source, or a family rotation after recording this zero-lead prescreen. Any repair must count as new hypotheses before screening.
