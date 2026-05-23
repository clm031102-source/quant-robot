# Architecture

The phase-one framework is organized as a research pipeline:

```text
assets -> data adapters -> normalization -> storage -> factors -> labels -> evaluation -> backtest -> signals -> portfolio -> paper -> reports
```

Important boundaries:

- `assets` owns market identity and canonical asset metadata.
- `data.adapters` owns optional third-party data-source integration.
- `data.normalize` converts source-shaped OHLCV data into the canonical schema.
- `storage` owns deterministic local persistence.
- `factors` computes only features available at or before the signal date.
- `research` creates labels and evaluates factor quality.
- `backtest` converts factor ranks into research returns using delayed execution.
- `signals` converts approved factor definitions into latest target-weight snapshots.
- `portfolio` applies local risk caps and produces research-only advisory rebalance plans.
- `paper` simulates intents, fills, cash, positions, and equity without live execution.
- `reports` writes human-readable outputs.

The core package can run without live data dependencies. Optional adapters are intentionally thin so AKShare, Tushare, yfinance, and ccxt can change without forcing research modules to change.

The `signals`, `portfolio`, and `paper` layers are intentionally still local and research-only. They create target weights, advisory deltas, and simulated fills that can be inspected and saved, but they do not include broker routing, account login, or order placement.
