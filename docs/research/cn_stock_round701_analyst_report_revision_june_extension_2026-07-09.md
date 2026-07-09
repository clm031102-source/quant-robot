# CN Stock Round701 Analyst Report Revision June Extension

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round701 used the remaining local daily `report_rc` request budget to extend the frozen analyst-report revision source from January-May 2024 through June 2024, then reran the same PIT/IC prescreen on January-June 2024.

This was a controlled source extension plus frozen prescreen only. It did not run portfolio grids, walk-forward portfolio validation, promotion gates, sign/window tuning, formula tuning, mixed-window harvesting, signal generation, or 2026 final-holdout reads.

## Startup And Quota Control

Fresh startup evidence for this continuation:

- Quant PM startup gate: `ready`, blockers `[]`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`, commits allowed true, pushes allowed false.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

Quota preflight command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-06-01 --end-date 2024-06-30 --output-dir data\reports\round701_analyst_report_revision_cache_202406_20260709 --processed-output-dir data\processed\round701_analyst_report_revision_cache_202406_20260709 --window-frequency MS --request-sleep-seconds 0 --quota-output-dir data\reports\round701_analyst_report_quota_preflight_20260709 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-preflight-only
```

Preflight result:

| Metric | Value |
| --- | ---: |
| Request allowed | true |
| Counted same-day request windows | 1 |
| Remaining request windows | 1 |
| Blockers | 0 |
| Warning | `local_report_roots_only` |

## June Cache

Provider request command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-06-01 --end-date 2024-06-30 --output-dir data\reports\round701_analyst_report_revision_cache_202406_20260709 --processed-output-dir data\processed\round701_analyst_report_revision_cache_202406_20260709 --window-frequency MS --request-sleep-seconds 0 --quota-output-dir data\reports\round701_analyst_report_quota_preflight_20260709 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705
```

Output:

```text
data/reports/round701_analyst_report_revision_cache_202406_20260709
data/processed/round701_analyst_report_revision_cache_202406_20260709
```

Cache result:

| Metric | Value |
| --- | ---: |
| Rows | 1,880 |
| Assets | 1,075 |
| Fetched windows | 1 |
| Failed windows | 0 |
| Rate-limited windows | 0 |
| Row-cap warning windows | 0 |
| Min report date | 2024-06-10 |
| Max report date | 2024-06-30 |

Postcheck:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-07-01 --end-date 2024-07-31 --output-dir data\reports\round701_analyst_report_revision_cache_202407_postcheck_20260709 --processed-output-dir data\processed\round701_analyst_report_revision_cache_202407_postcheck_20260709 --window-frequency MS --request-sleep-seconds 0 --quota-output-dir data\reports\round701_analyst_report_quota_postcheck_20260709 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-preflight-only
```

Postcheck result: blocked with `daily_provider_request_budget_exhausted`, counted provider request windows `2`, remaining request windows `0`. No July provider request was sent.

## Frozen Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round507_analyst_report_revision_cache_202404_20260707 --report-root data\processed\round700_analyst_report_revision_cache_202405_20260709 --report-root data\processed\round701_analyst_report_revision_cache_202406_20260709 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round701_analyst_report_revision_jan_jun_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 30 --min-ic-observations 8
```

Output:

```text
data/reports/round701_analyst_report_revision_jan_jun_prescreen_20260709
```

Summary:

| Metric | Value |
| --- | ---: |
| Candidate count | 4 |
| Test count | 8 |
| Report rows | 10,509 |
| Report assets | 2,226 |
| Factor rows | 24,781 |
| Aligned rows | 49,562 |
| Min report date | 2024-01-25 |
| Max report date | 2024-06-30 |
| Max signal date | 2024-07-01 |
| Multiple-testing leads | 4 |
| Neutral-gate passes | 2 |
| Research leads | 0 |
| Promotion allowed candidates | 0 |
| Year-coverage pass count | 0 |
| Final holdout included | false |

Top rows:

| Factor | H | IC | ICIR | t | p | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | FDR | Lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `analyst_target_upside_60` | 5 | 0.1511 | 0.577 | 3.74 | 0.0002 | 76.2% | 0.0223 | 0.4182 | 0.1146 | yes | no |
| `analyst_target_upside_60` | 20 | 0.0860 | 0.425 | 2.75 | 0.0059 | 73.8% | 0.0263 | 0.3953 | 0.0521 | yes | no |
| `analyst_revision_target_composite_90` | 20 | 0.0510 | 0.379 | 2.51 | 0.0120 | 68.2% | 0.0099 | 0.4340 | 0.0425 | yes | no |
| `analyst_revision_target_composite_90` | 5 | 0.0432 | 0.350 | 2.32 | 0.0204 | 65.9% | 0.0099 | 0.4047 | 0.0251 | yes | no |
| `analyst_eps_revision_90` | 20 | 0.0323 | 0.245 | 1.61 | 0.1080 | 60.5% | 0.0111 | 0.4078 | 0.0341 | no | no |
| `analyst_np_revision_90` | 20 | 0.0302 | 0.224 | 1.47 | 0.1416 | 60.5% | 0.0131 | 0.4055 | 0.0319 | no | no |
| `analyst_eps_revision_90` | 5 | 0.0205 | 0.164 | 1.08 | 0.2822 | 58.1% | 0.0048 | 0.3819 | 0.0185 | no | no |
| `analyst_np_revision_90` | 5 | 0.0161 | 0.123 | 0.81 | 0.4198 | 58.1% | 0.0058 | 0.3808 | 0.0138 | no | no |

## Decision

Promising source accumulation, not a research lead yet.

The June extension materially improved the analyst-report revision screen: `analyst_target_upside_60` at horizon 5 now passes FDR and size-neutral checks with IC `0.1511`, ICIR `0.577`, t-stat `3.74`, positive IC rate `76.2%`, and positive Q5-Q1 spread `0.0223`. The composite 20-day signal also passes FDR and size-neutral checks.

The blocker is still decisive: all evidence is from one IC year, so `year_coverage_pass_count=0` and `research_lead_count=0`. No portfolio conversion is allowed.

Allowed next action after quota reset:

- cache the next monthly `report_rc` window with the same quota preflight discipline;
- rerun the same frozen prescreen without formula, sign, or threshold changes;
- continue only while the top rows keep passing FDR/neutral gates and the work is framed as source accumulation, not alpha promotion.

Blocked actions:

- no portfolio grid;
- no walk-forward conversion;
- no target-upside formula tuning;
- no sign/window tuning;
- no threshold relaxation;
- no 2026 final-holdout read;
- no same-day extra provider request after the postcheck exhausted the local daily budget.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
