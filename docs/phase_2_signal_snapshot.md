# Phase 2 Signal Snapshot

Signal snapshot generation is the bridge from factor research to a later simulated trading loop.

It is still research-only. It does not connect to brokers, read real accounts, or place orders.

## What It Does

- filters local fixture or processed bars to an `as_of_date`;
- computes the configured factor without using future bars;
- selects top-ranked assets with market or global portfolio scope;
- applies local risk caps for asset weight, market weight, gross exposure, and cash;
- writes latest target weights;
- writes an advisory rebalance plan with `executable=false`.

## Command

```powershell
$env:PYTHONPATH='src'
python scripts\run_signal_snapshot.py --source fixture --market ALL --factor momentum_2 --top-n 2
```

Default output:

```text
data/reports/signal_snapshot/
```

## Output Files

- `targets.csv`: current target weights, latest local prices, factor values, and signal date.
- `rebalance_plan.csv`: advisory deltas from a local paper-position input to the target weights.
- `manifest.json`: request, constraints, data mode, signal date, cash weight, and warnings.

## Optional Positions CSV

To compare the target weights against a local paper portfolio, pass:

```powershell
--positions-csv path\to\positions.csv
```

The CSV must contain only:

```text
asset_id,quantity
```

Columns such as `account_id`, `broker`, or `order_id` are rejected to keep this stage separated from real accounts.

## Risk Controls

Use these CLI flags to keep generated targets conservative:

- `--max-asset-weight`
- `--max-market-weight`
- `--max-gross-exposure`
- `--min-cash-weight`

Caps leave unused weight in cash rather than forcing full investment. This is deliberate: the signal layer should prefer under-allocation over hidden leverage.
