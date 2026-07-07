# CN Stock Round661 Financial Reporting Timeliness Backfill Progress

Date: 2026-07-08

Branch: `codex/data-pipeline-financial-timeliness-round661-20260708`

Scope: continue the financial reporting timeliness / PIT statement data-pipeline backfill from clean `main` after Round660. This round used shard 52 offset 0 limit 5, reran explicit all-root aggregate source audits, and previewed the next net-new window. It did not run factor generation, IC screens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, after Round660 was merged |
| New branch | `codex/data-pipeline-financial-timeliness-round661-20260708` |
| Startup context | `office_desktop` / `data_pipeline`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| Preflight source audit | blocked at 852 / 1,000 unique symbols using `--financial-root data\processed` |
| Sync audit before provider work | no syncable files, blockers `[]`, branch discovery errors `[]`, remote topic branches `0` |
| Single-instance check | no active backfill |
| Research market | `CN_ETF` primary; CN stock work remains data-pipeline / research support only |
| Live-trading boundary | no broker connection, account reads, orders, or automatic trading |

## Preflight Source Audit

| Metric | Value |
| --- | ---: |
| Status | blocked |
| Source count | 211 |
| Row count | 180,398 |
| Unique symbols | 852 |
| Minimum required symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

Gate blocker before provider work:

```text
unique_symbol_count_below_minimum
```

## Net-New Selection

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 52 offset 0 limit 5 | 211 | 5 | 0 | 5 |

Selected symbols:

- `600000.SH`
- `002286.SZ`
- `300673.SZ`
- `601069.SH`
- `002376.SZ`

## Backfill Results

| Metric | Value |
| --- | ---: |
| Passes | true |
| Symbols | 5 |
| Planned symbol-periods | 220 |
| Active symbol-periods | 220 |
| Pre-listing skipped symbol-periods | 0 |
| Endpoint requests | 660 |
| Pre-listing skipped endpoint requests | 0 |
| Empty requests | 8 |
| Processed rows | 219 |
| Duplicate rows in quality report | 1 |
| Required column groups passing | 2 / 2 |
| Blockers | `[]` |

Quality report:

| Metric | Value |
| --- | ---: |
| Assets | 5 |
| Rows | 219 |
| Missing asset-id rows | 0 |
| Duplicate rows | 1 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-21 to 2026-04-25 |

The quality report passed with blockers `[]` and 0 missing asset-id rows. It reported 1 duplicate row. A targeted inspection located the duplicate key at `CN_XSHG_601069` / `601069.SH`, `end_date=2025-03-31`, `ann_date=2025-04-29`; the two rows differ in `end_type` and several statement values. This remains source-only evidence and does not authorize factor generation.

## Post-Backfill Source Audit

| Metric | Round660 After Backfill | Round661 After Backfill |
| --- | ---: | ---: |
| Status | blocked | blocked |
| Source count | 211 | 212 |
| Row count | 180,398 | 181,509 |
| Unique symbols | 852 | 857 |
| Minimum required symbols | 1,000 | 1,000 |
| Source-ready count | 0 | 0 |
| Candidate plan allowed | false | false |

Gate blocker remains:

```text
unique_symbol_count_below_minimum
```

## Next Window Preview

Shard 52 offset 5 limit 5 previewed as 5 / 5 net-new.

| Preview | Financial roots | Symbols | Existing | Net-new |
| --- | ---: | ---: | ---: | ---: |
| shard 52 offset 5 limit 5 | 212 | 5 | 0 | 5 |

Next candidate symbols:

- `002265.SZ`
- `002166.SZ`
- `001318.SZ`
- `002315.SZ`
- `002682.SZ`

## Decision

Round661 expanded the local source by another five net-new symbols, but financial reporting timeliness remains blocked at the source gate. Continue audited net-new backfill only in small windows, moving to shard 52 offset 5 limit 5 after starting from merged `main`. Do not preregister or test factors from the current cache.
