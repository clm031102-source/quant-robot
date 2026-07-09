# CN Stock Round698 HK-Hold Quarterly Policy Audit

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round698 checked whether the Round697 HK-hold source anomaly is a local ingestion bug or a source-policy change. The result points to a source-policy change: the Tushare `hk_hold` endpoint still returns CN-suffixed rows on quarter-end dates, but tested non-quarter post-2024-08-16 dates returned HK-suffixed rows only.

This round did not run IC tests, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, signal generation, or 2026 final-holdout reads.

## Official Source Note

Tushare official `hk_hold` documentation:

- [Tushare hk_hold document](https://tushare.pro/wctapi/documents/188.md)

The document states that the exchange stopped daily northbound holding publication from 2024-08-20 and changed to quarterly disclosure. Treat this as source-policy evidence, not alpha evidence.

## Quarterly Source Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_hk_hold_source_audit.py --trade-date 2024-09-30 --trade-date 2024-12-31 --trade-date 2025-03-31 --trade-date 2025-06-30 --trade-date 2025-09-30 --trade-date 2025-12-31 --output-dir data\reports\round698_hk_hold_quarterly_policy_audit_20260709
```

Output path:

```text
data/reports/round698_hk_hold_quarterly_policy_audit_20260709
```

Summary:

| Metric | Value |
| --- | ---: |
| Requested dates | 6 |
| Raw rows | 24,128 |
| CN rows | 20,744 |
| Non-CN rows | 3,384 |
| CN row ratio | 0.8597 |
| Usable CN dates | 6 |
| Empty after CN filter dates | 0 |
| Empty raw dates | 0 |

Suffix totals:

| Suffix | Rows |
| --- | ---: |
| HK | 3,384 |
| SH | 10,744 |
| SZ | 10,000 |

Date rows:

| Trade date | Status | Raw rows | CN rows | Non-CN rows | Suffix counts |
| --- | --- | ---: | ---: | ---: | --- |
| 2024-09-30 | `usable_cn_rows` | 3,540 | 3,540 | 0 | SH 1,703, SZ 1,837 |
| 2024-12-31 | `usable_cn_rows` | 4,200 | 3,385 | 815 | HK 815, SH 1,733, SZ 1,652 |
| 2025-03-31 | `usable_cn_rows` | 4,200 | 3,366 | 834 | HK 834, SH 1,756, SZ 1,610 |
| 2025-06-30 | `usable_cn_rows` | 3,788 | 3,788 | 0 | SH 1,815, SZ 1,973 |
| 2025-09-30 | `usable_cn_rows` | 4,200 | 3,340 | 860 | HK 860, SH 1,830, SZ 1,510 |
| 2025-12-31 | `usable_cn_rows` | 4,200 | 3,325 | 875 | HK 875, SH 1,907, SZ 1,418 |

## Decision

The existing `hk_hold` source should not be treated as a repairable daily CN-stock feed after 2024-08-20. It is a quarterly northbound holding source under the current provider policy.

Allowed use:

- Low-frequency state features that explicitly model quarterly updates and available-date lag.
- Source-control or regime-control context when paired with a valid cross-sectional factor.
- Future candidate plans only if they use a quarterly-state design and pass the normal preregistration gate before any IC screen.

Blocked use:

- Daily HK-hold rank factors after 2024-08-20.
- Blind daily backfill attempts to clear the 60-observation history requirement.
- Lowering the existing 60-observation threshold after seeing source coverage.
- Treating Round697 or Round698 source audits as alpha, portfolio, promotion, or live evidence.
- Final-holdout reads.

Practical next step: rotate away from HK-hold x LPR as an immediate active stock factor. If HK-hold is revisited, preregister it as a low-frequency quarterly state family with explicit lag and stale-state controls rather than a daily extension problem.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
