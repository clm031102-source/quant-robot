# Phase 2 Paper Simulation

Paper simulation is the next bridge after signal snapshots. It turns local research signals into simulated intents, simulated fills, cash, positions, and an equity curve.

It is still research-only. It does not connect to brokers, read real accounts, or place orders.

## What It Does

- generates a signal snapshot for each eligible signal date;
- builds a local advisory rebalance plan from current simulated positions;
- converts advisory deltas into paper simulation intents marked `executable=false`;
- executes simulated fills only when the asset has a real bar on the execution date;
- applies configurable commission and slippage assumptions;
- updates simulated cash and positions;
- writes an equity curve and final metrics.

## Command

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_simulation.py --source fixture --market ALL --factor momentum_2 --top-n 2
```

Default output:

```text
data/reports/paper_simulation/
```

## Output Files

- `intents.csv`: research-only desired paper actions, all with `executable=false`.
- `fills.csv`: simulated fills with fill price, quantity, notional, and fees.
- `positions.csv`: final simulated positions.
- `equity_curve.csv`: cash, equity, gross exposure, and period return.
- `snapshots.csv`: signal-date target summaries.
- `guard_events.csv`: drawdown guard trigger and buy-block events, when a guard is configured.
- `manifest.json`: request, metrics, and safety boundary.

## Local GUI

The local GUI exposes the same demo paper loop through the `模拟交易` page and `/api/paper/demo` endpoint. It is useful for inspecting equity, gross exposure, simulated fills, and final positions without leaving the browser.

## Safety Boundary

The simulator accepts an optional local positions CSV, but only with:

```text
asset_id,quantity
```

Columns such as `account_id`, `broker`, or `order_id` are rejected. This keeps the paper layer separated from real accounts and live execution.

## Modeling Limits

The first implementation uses daily bars and simple fill assumptions. It is useful for workflow validation and strategy sanity checks, not proof of profitability. Later phases should add richer market calendars, lot sizes, limit-up/down handling, suspended assets, and more realistic execution models before any small-money live experiment.

For mixed-market runs, prior prices may be used to value existing positions on days when a market is closed, but they are not used to create simulated fills. Reported `total_return` and `cash_return` both use starting equity as the denominator.

Phase 2.6 adds an optional drawdown guard. When `--max-drawdown-guard` is breached, the simulator records a guard event and blocks new buy intents during `--guard-cooldown-periods`; sell intents remain allowed so the simulated portfolio can reduce exposure.
