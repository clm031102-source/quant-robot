# CN Stock Round453 Analyst Report Revision Source Smoke

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

## Purpose

Round453 rotated away from the `entry_limit_down` execution-risk line into a genuinely different PIT source: Tushare `report_rc` analyst reports. The intent was to test analyst target price, EPS, net-profit forecast, rating, and revision signals as external expectation factors.

## Pre-Registered Candidates

- `analyst_target_upside_60`
- `analyst_np_revision_90`
- `analyst_eps_revision_90`
- `analyst_revision_target_composite_90`

The candidate-plan gate cleared. These candidates remained source-screen only; portfolio grids and promotion were blocked before source availability, PIT alignment, full 2015-2025 replay, OOS, cost, capacity, regime, and multiple-testing checks.

## Source Smoke Result

Command:

`python scripts\run_tushare_analyst_report_cache.py --start-date 2024-01-01 --end-date 2024-01-31 --output-dir data\reports\round453_analyst_report_revision_source_smoke_jan2024_20260627 --processed-output-dir data\processed\round453_analyst_report_revision_source_smoke_jan2024_20260627 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000`

Result:

- windows: 1
- fetched windows: 0
- failed windows: 1
- rows: 0
- assets: 0
- failure: Tushare `report_rc` frequency limit exceeded, reported as 2 requests per day.

Report:

`data/reports/round453_analyst_report_revision_source_smoke_jan2024_20260627/tushare_analyst_report_cache.json`

## Decision

Do not continue analyst-report revision mining during this 24h sprint unless a local cached PIT report source is discovered. The source has a strong economic hypothesis, but the provider limit prevents building a statistically useful sample in time.

Round453 produces:

- new independent alpha factors: 0
- usable research leads: 0
- valid process improvement: 1, an explicit provider-limit source gate

## Next Direction

Move to Round454 with a fast source-efficiency decision. Do not spend the next work block on slow endpoint accumulation if the source coverage gate remains far from candidate readiness.
