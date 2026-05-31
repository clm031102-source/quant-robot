# Phase 2.6 Decision Risk Layer

Phase 2.6 adds a research-only decision layer between factor mining and any simulated deployment decision.

It does not connect to brokers, read accounts, place orders, or make live-trading decisions.

## What It Adds

- Benchmark comparison for each research run.
- Cash comparison through a configurable annual cash return.
- Optional regime filter based on benchmark momentum.
- Decision summaries with `approved` or `rejected` status.
- Walk-forward rejection gates for relative return and maximum drawdown.
- Paper-simulation drawdown guard that blocks new buy intents during a cooldown window.

## Research Pipeline

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source fixture --market CN_ETF --factor momentum_2 --top-n 1 --benchmark-asset-id CN_ETF_XSHG_510300 --cash-annual-return 0.015 --regime-filter --regime-lookback 3 --min-relative-return 0 --max-drawdown-limit 0.25
```

New artifacts:

- `benchmark_curve.csv`
- `benchmark_metrics.json`
- `decision.json`
- `regime_curve.csv`

Important fields:

- `benchmark_total_return`
- `relative_return`
- `excess_over_cash`
- `decision_status`
- `rejection_reasons`

## Experiment Grid

Grid configs can include:

```json
{
  "benchmark_asset_id": "CN_ETF_XSHG_510300",
  "cash_annual_return": 0.015,
  "regime_filter": true,
  "regime_lookback": 60,
  "min_relative_return": 0,
  "max_drawdown_limit": 0.25,
  "rank_by": "relative_return"
}
```

The leaderboard includes benchmark and decision columns. A rejected decision row can still be inspected as a completed research case; rejection is a research finding, not a process failure.

## Walk-Forward Validation

Walk-forward configs can add:

```json
{
  "min_test_relative_return": 0,
  "max_test_drawdown": 0.25
}
```

Candidates can now be rejected for:

- `relative_return_below_threshold`
- `drawdown_above_limit`

## Paper Simulation Guard

The simulator can block new buy intents after a configured equity drawdown breach:

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_simulation.py --source fixture --market CN_ETF --factor momentum_2 --top-n 1 --max-drawdown-guard 0.10 --guard-cooldown-periods 5
```

Sell intents remain allowed while guarded. This keeps the guard conservative: it can reduce exposure, but it cannot add new long exposure during cooldown.

New output:

- `guard_events.csv`

## Interpretation

An `approved` decision means only that the candidate passed configured local research gates. It is not a live-trading signal. Real-data runs still require stronger data coverage, broader ETF universes, execution modeling, and manual review before any small-capital experiment.
