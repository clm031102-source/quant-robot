# Phase 2 Walk-Forward Validation

Walk-forward validation adds the first overfitting guard to the local research loop.

It is still research-only. It does not connect to brokers, place orders, or run live trading.

## Why This Exists

A batch experiment grid can find candidates that look good on one data slice. That is not enough. A candidate has to survive an out-of-sample period before it is worth deeper research.

The walk-forward runner:

- splits bars by `split_date`;
- runs the same experiment grid on train data and test data;
- carries enough pre-split warmup bars into the test calculation for rolling factors;
- filters test signals so out-of-sample trades start only after the split;
- merges train/test metrics by `case_id`;
- computes `sharpe_degradation` and `stability_score`;
- marks candidates as `accepted` or `rejected`;
- writes a leaderboard for review.

## Command

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --source fixture
```

Default config:

```text
configs/walk_forward.json
```

Default output:

```text
data/reports/walk_forward/
```

## Output Files

- `walk_forward_leaderboard.csv`: train/test comparison table.
- `walk_forward_leaderboard.json`: structured output for future GUI/API use.
- `manifest.json`: split date, thresholds, grid config, and summary.
- `train/`: train-period experiment artifacts.
- `test/`: out-of-sample experiment artifacts.

## Important Fields

- `validation_status`: `accepted` only means the candidate passed configured local thresholds.
- `rejection_reasons`: explains failed gates, such as insufficient test trades or weak out-of-sample Sharpe.
- `train_sharpe` / `test_sharpe`: compare in-sample and out-of-sample behavior.
- `sharpe_degradation`: positive when train Sharpe is higher than test Sharpe.
- `stability_score`: test Sharpe penalized by train-to-test degradation.
- `data_mode`: `fixture` means demo data only, not evidence of real profitability.

## Warmup And No-Lookahead

Rolling factors need historical bars before the first test date. The test run receives per-asset warmup bars from the train period, but those warmup bars are only used to calculate state. Signals and trades are filtered to the first post-split date or later, so train-period rows cannot become test-period trades.

## Real Data Later

After real processed bars exist, run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --source processed-bars --data-root data\processed\tushare_fixture
```

The same flow can later be used with yfinance, AKShare, or ccxt processed bars once those adapters produce the unified schema.
