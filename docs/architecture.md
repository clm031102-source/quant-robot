# Architecture

The phase-one framework is organized as a research pipeline:

```text
assets -> data adapters -> normalization -> storage -> factors -> labels -> evaluation -> backtest -> reports
```

Important boundaries:

- `assets` owns market identity and canonical asset metadata.
- `data.adapters` owns optional third-party data-source integration.
- `data.normalize` converts source-shaped OHLCV data into the canonical schema.
- `storage` owns deterministic local persistence.
- `factors` computes only features available at or before the signal date.
- `research` creates labels and evaluates factor quality.
- `backtest` converts factor ranks into research returns using delayed execution.
- `reports` writes human-readable outputs.

The core package can run without live data dependencies. Optional adapters are intentionally thin so AKShare, Tushare, yfinance, and ccxt can change without forcing research modules to change.
