# Phase 2 Experiment Grid

Phase 2 starts the local factor-mining loop. It is still research-only: no broker connection, no order placement, no account login, and no live execution.

## Goal

Run many local research/backtest cases from one configuration file, then rank the results in a reproducible leaderboard.

The first grid runner supports:

- markets: CN, HK, US, CRYPTO;
- factor names from the current basic factor library;
- multiple transaction-cost assumptions;
- multiple `top_n` portfolio sizes;
- per-case artifacts from the research pipeline;
- a combined leaderboard with explicit `data_mode`.

## Default Command

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_experiment_grid.py --source fixture
```

Default config:

```text
configs/experiment_grid.json
```

Default output:

```text
data/reports/experiment_grid/
```

## Output Files

- `leaderboard.csv`: sortable table for Excel or pandas review.
- `leaderboard.json`: structured leaderboard for later GUI/API use.
- `manifest.json`: run config and case summary.
- `<case_id>/`: per-case metrics, IC, group returns, long-short returns, trades, holdings, and SVG charts.

## Interpreting Results

Fixture runs prove the pipeline works; they do not prove a strategy can make money. Any fixture leaderboard row must be treated as demo-only.

When real processed bars exist, use:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_experiment_grid.py --source processed-bars --data-root data\processed\tushare_fixture
```

For real Tushare data later, install optional dependencies, set `TUSHARE_TOKEN`, ingest data, then point `--data-root` at the ingest output root or a parent directory containing processed bars.
