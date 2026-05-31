# Phase 2 Experiment Grid

Phase 2 starts the local factor-mining loop. It is still research-only: no broker connection, no order placement, no account login, and no live execution.

## Goal

Run many local research/backtest cases from one configuration file, then rank the results in a reproducible leaderboard.

The first grid runner supports:

- markets: CN, CN_ETF, HK, US, CRYPTO;
- factor names from the current basic factor library;
- multiple transaction-cost assumptions;
- multiple `top_n` portfolio sizes;
- configurable `forward_horizon` and `execution_lag`;
- conservative signal-sleeve scaling when `forward_horizon` is greater than one, so daily overlapping research signals do not implicitly assume a full new portfolio for each holding window;
- optional `portfolio_scope` and `periods_per_year` overrides;
- optional benchmark/cash comparison and regime filtering from Phase 2.6;
- per-case artifacts from the research pipeline;
- a combined leaderboard with explicit `data_mode`.

## Default Command

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --source fixture
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

The grid validates that known factor names match `factor_windows`. For example, `momentum_20` requires `20` in `factor_windows`; otherwise the run fails early. This prevents a typo from turning into a silent no-trade leaderboard row.

The CLI also fails the process when any case has `status=failed` or when no case completes. Failed rows can still be inspected in `leaderboard.csv` and `leaderboard.json`, but `run_checks.py --execute` will not treat that run as healthy.

Phase 2.6 adds decision-risk fields to each completed row: `benchmark_total_return`, `relative_return`, `excess_over_cash`, `decision_status`, and `decision_reasons`. These fields help decide whether a candidate deserves more research; they do not make a live-trading decision.

For multi-market cases, leave `portfolio_scope` unset unless you need a specific override. The research pipeline uses `global` scope for `market=ALL` so total target weight is capped across markets, and `market` scope for single-market runs. `periods_per_year` can be set explicitly when you want to override the default annualization assumption; otherwise crypto uses 365 and non-crypto markets use 252.

When real processed bars exist, use:

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --source processed-bars --data-root data\processed\tushare_fixture
```

For real Tushare data later, install optional dependencies, set `TUSHARE_TOKEN`, ingest data, then point `--data-root` at the ingest output root or a parent directory containing processed bars.

For ETF-only factor mining, use:

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_etf.json --source processed-bars --data-root data\processed\etf_csv
```
