# CN Stock Round700 Analyst Report Revision May Extension

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round700 spent one controlled Tushare `report_rc` request window to extend the frozen analyst-report revision source from January-April 2024 through May 2024, then reran the same PIT/IC prescreen on January-May 2024.

This was a source extension plus frozen prescreen only. It did not run portfolio grids, walk-forward portfolio validation, promotion gates, sign/window tuning, formula tuning, mixed-window harvesting, signal generation, or 2026 final-holdout reads.

## Startup And Quota Gate

The Quant PM startup gate was rerun before the provider request:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709
```

Result: `ready`, blockers `[]`, primary market `CN_ETF`.

Quota preflight command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-05-01 --end-date 2024-05-31 --output-dir data\reports\round700_analyst_report_revision_cache_202405_20260709 --processed-output-dir data\processed\round700_analyst_report_revision_cache_202405_20260709 --window-frequency MS --request-sleep-seconds 0 --quota-output-dir data\reports\round700_analyst_report_quota_preflight_20260709 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-preflight-only
```

Preflight result:

| Metric | Value |
| --- | ---: |
| Request allowed | true |
| Blockers | 0 |
| Same-day counted windows | 0 |
| Remaining request windows | 2 |
| Quota warning | `local_report_roots_only` |

## May Cache

Provider request command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-05-01 --end-date 2024-05-31 --output-dir data\reports\round700_analyst_report_revision_cache_202405_20260709 --processed-output-dir data\processed\round700_analyst_report_revision_cache_202405_20260709 --window-frequency MS --request-sleep-seconds 0 --quota-output-dir data\reports\round700_analyst_report_quota_preflight_20260709 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705
```

Output:

```text
data/reports/round700_analyst_report_revision_cache_202405_20260709
data/processed/round700_analyst_report_revision_cache_202405_20260709
```

Cache result:

| Metric | Value |
| --- | ---: |
| Rows | 1,801 |
| Assets | 1,072 |
| Fetched windows | 1 |
| Failed windows | 0 |
| Rate-limited windows | 0 |
| Row-cap warning windows | 0 |
| Min report date | 2024-05-19 |
| Max report date | 2024-05-31 |

## Frozen Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round507_analyst_report_revision_cache_202404_20260707 --report-root data\processed\round700_analyst_report_revision_cache_202405_20260709 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round700_analyst_report_revision_jan_may_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 30 --min-ic-observations 8
```

Output:

```text
data/reports/round700_analyst_report_revision_jan_may_prescreen_20260709
```

Summary:

| Metric | Value |
| --- | ---: |
| Candidate count | 4 |
| Test count | 8 |
| Report rows | 8,629 |
| Report assets | 2,039 |
| Factor rows | 18,969 |
| Aligned rows | 37,938 |
| Min report date | 2024-01-25 |
| Max report date | 2024-05-31 |
| Max signal date | 2024-06-03 |
| Multiple-testing leads | 0 |
| Neutral-gate passes | 0 |
| Research leads | 0 |
| Promotion allowed candidates | 0 |
| Year-coverage pass count | 0 |
| Final holdout included | false |

Top rows:

| Factor | H | IC | ICIR | t | p | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `analyst_target_upside_60` | 5 | 0.0940 | 0.339 | 1.80 | 0.0726 | 71.4% | 0.0156 | 0.4129 | 0.0575 | no |
| `analyst_target_upside_60` | 20 | 0.0477 | 0.233 | 1.23 | 0.2180 | 67.9% | 0.0136 | 0.3882 | 0.0137 | no |
| `analyst_eps_revision_90` | 20 | 0.0395 | 0.283 | 1.50 | 0.1347 | 67.9% | 0.0105 | 0.4072 | 0.0396 | no |
| `analyst_np_revision_90` | 20 | 0.0385 | 0.270 | 1.43 | 0.1530 | 67.9% | 0.0130 | 0.4068 | 0.0386 | no |
| `analyst_revision_target_composite_90` | 20 | 0.0367 | 0.268 | 1.44 | 0.1492 | 65.5% | 0.0021 | 0.4234 | 0.0276 | no |
| `analyst_revision_target_composite_90` | 5 | 0.0290 | 0.243 | 1.31 | 0.1912 | 65.5% | 0.0068 | 0.4034 | 0.0011 | no |
| `analyst_np_revision_90` | 5 | 0.0227 | 0.172 | 0.91 | 0.3618 | 67.9% | 0.0074 | 0.3723 | 0.0170 | no |
| `analyst_eps_revision_90` | 5 | 0.0205 | 0.167 | 0.88 | 0.3775 | 64.3% | 0.0049 | 0.3677 | 0.0153 | no |

## Decision

Rejected for factor conversion.

The May cache succeeded and expanded the analyst-report source to 8,629 January-May rows across 2,039 assets, but the frozen prescreen still produced zero multiple-testing leads, zero neutral-gate passes, zero research leads, and zero promotion-allowed candidates. The best row, `analyst_target_upside_60` at horizon 5, had positive raw IC but failed FDR and size-neutral gates, with only one IC year of coverage.

Do not continue this evidence into:

- formula tuning;
- sign flips;
- portfolio grids;
- walk-forward conversion;
- promotion gates;
- threshold relaxation;
- final-holdout reads.

Next action: rotate away from analyst-report revision unless the explicit objective is slow source accumulation under quota governance. A future cache-only task may add history, but profitability claims remain blocked until a frozen prescreen clears multiple-testing, neutral, and coverage gates.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
