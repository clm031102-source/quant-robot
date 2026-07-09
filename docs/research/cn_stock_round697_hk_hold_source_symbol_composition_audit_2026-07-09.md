# CN Stock Round697 HK-Hold Source Symbol Composition Audit

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round697 added and ran a source-audit tool for raw Tushare `hk_hold` symbol composition. The goal was to explain why Round696 could not extend CN-stock HK-hold history after 2024-08-16.

This round did not run IC tests, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, signal generation, or 2026 final-holdout reads.

## Tooling Added

Added a read-only audit entrypoint:

```text
scripts/run_tushare_hk_hold_source_audit.py
```

Core operation:

```text
src/quant_robot/ops/tushare_hk_hold_source_audit.py
```

The audit records, per requested trade date:

- raw `hk_hold` row count;
- CN rows by stock suffix `.SH`, `.SZ`, `.BJ`;
- non-CN rows, including `.HK`;
- status: `usable_cn_rows`, `empty_after_cn_filter`, or `empty_raw_response`;
- sample CN and non-CN symbols.

The tool writes only under `data/reports` by default and sets `promotion_allowed=false`.

## Startup And Gate Evidence

- Startup context: passed for `office_desktop` / `factor_batch`.
- Quant PM startup gate: `ready`, blockers `[]`, primary research market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`, branch matched `codex/factor-batch-cn-stock-source-readiness-round695-20260709`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

## Source Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_hk_hold_source_audit.py --trade-date 2024-08-16 --trade-date 2024-08-19 --trade-date 2024-10-08 --trade-date 2024-10-31 --output-dir data\reports\round697_hk_hold_source_symbol_composition_audit_20260709
```

Output path:

```text
data/reports/round697_hk_hold_source_symbol_composition_audit_20260709
```

Summary:

| Metric | Value |
| --- | ---: |
| Requested dates | 4 |
| Raw rows | 6,550 |
| CN rows | 3,337 |
| Non-CN rows | 3,213 |
| CN row ratio | 0.5095 |
| Usable CN dates | 1 |
| Empty after CN filter dates | 3 |
| Empty raw dates | 0 |

Suffix totals:

| Suffix | Rows |
| --- | ---: |
| HK | 3,213 |
| SH | 1,573 |
| SZ | 1,764 |

Date rows:

| Trade date | Status | Raw rows | CN rows | Non-CN rows | Suffix counts |
| --- | --- | ---: | ---: | ---: | --- |
| 2024-08-16 | `usable_cn_rows` | 4,128 | 3,337 | 791 | HK 791, SH 1,573, SZ 1,764 |
| 2024-08-19 | `empty_after_cn_filter` | 792 | 0 | 792 | HK 792 |
| 2024-10-08 | `empty_after_cn_filter` | 816 | 0 | 816 | HK 816 |
| 2024-10-31 | `empty_after_cn_filter` | 814 | 0 | 814 | HK 814 |

Interpretation:

- The provider endpoint is not empty on the probed post-2024-08-16 dates.
- The returned rows are valid raw rows, but they are HK-suffixed symbols only for the tested post-2024-08-16 dates.
- The CN-stock pipeline correctly drops those rows for CN cross-sectional research.
- Blind daily extension of the current `hk_hold` feed cannot clear the preregistered 60-observation HK-hold x LPR requirement.

## Decision

Do not run HK-hold x LPR factor generation, IC screens, portfolio grids, or promotion gates from the current HK-hold source state.

Allowed next actions:

- Search for an alternative Tushare endpoint or field mode that returns northbound CN holdings after 2024-08-16.
- If a valid extension path is found, rerun this symbol-composition audit before writing processed data.
- Rerun external-feed coverage and join smoke only after CN-suffixed observation history is extended without lowering the preregistered 60-observation threshold.
- Use pure LPR only as a market-regime control for an already valid cross-sectional factor, not as a standalone stock-rank alpha.

Blocked actions:

- No HK-hold x LPR IC screen before history readiness.
- No standalone LPR stock rank.
- No old external northbound or margin reentry.
- No threshold lowering after seeing the source audit.
- No final-holdout read.

## Verification

Unit tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_tushare_hk_hold_source_audit.py tests\unit\test_tushare_hk_hold_source_audit_cli.py -q
```

Result: `3 passed`.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
