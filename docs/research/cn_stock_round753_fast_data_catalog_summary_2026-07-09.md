# CN Stock Round753 Fast Data Catalog Summary

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round753 made the local data catalog usable as a fast source-discovery starting point. This supports the next no-provider path: finding genuinely new PIT-safe local source candidates instead of rerunning stale analyst prescreens or closed source families.

This round did not call a provider, download data, run a factor IC screen, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Change

`build_storage_catalog` now accepts:

- `include_datasets`: whether to materialize per-file dataset rows;
- `count_rows`: whether to count CSV rows.

`scripts/show_data_catalog.py --summary-only` now uses `include_datasets=false` and `count_rows=false`, so it avoids the expensive CSV row-count loop. When row counting is skipped or dataset details are omitted, `total_rows` is `null`, not `0`.

## Real Catalog Check

Command:

```powershell
.\.venv\Scripts\python.exe scripts\show_data_catalog.py --root data --summary-only
```

Result:

```json
{
  "root": "data",
  "total_bytes": 19646988047,
  "total_files": 404358,
  "total_rows": null
}
```

The full `data` tree still takes time to scan because it contains 404,358 data files, but the command now completes instead of spending the budget counting every CSV row.

## Tests

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_storage_catalog.py tests\unit\test_data_catalog_cli.py -q
```

Result: `5 passed`.

## Decision

This is tooling progress, not factor evidence. The next useful no-provider step is a quick local source inventory over `data/processed` and `data/reports`, using the fast catalog path to identify candidate PIT-safe source roots not already closed, hibernated, or quota-blocked in the local source queue.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
