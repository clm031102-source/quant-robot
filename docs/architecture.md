# Quant Robot v2 Architecture

## Design Principles

1. **Research-to-Paper Boundary**: The system computes signals, runs backtests, and maintains simulated paper ledgers only. It never connects to a broker or submits real orders.
2. **Data Integrity & Fault Tolerance**: Market bars are stored per `(market, symbol)` in `data/market_cache/`. Updates use retries with exponential backoff and overlap windows to detect corporate-action/split shifts. Missed days are caught up automatically rather than deadlocking.
3. **Strict T+1 Causality**: Every strategy reads only bars with `date <= T` and schedules execution for session `T+1` open/close.
4. **Realistic Friction Modeling**: Both backtests and paper ledgers enforce integer lot sizes (100 shares for CN ETFs, 1 share for US ETFs), minimum per-trade commissions (e.g., 5 CNY for Huabao CN ETFs, 1 USD for US ETFs), bps commissions, and adverse slippage.
5. **Single Codepath for Research & Paper**: Backtests (`backtest/simulator.py`) and live paper ledgers (`paper/ledger.py`) share the exact same strategy module (`strategies/builtins.py`) and cost/risk configs (`config/settings.py`).

## Data Flow

```text
Tushare / yfinance (with retry)
        │
        ▼
data/market_cache/<MARKET>/<SYMBOL>.parquet
        │
        ├──► scripts/run_backtest.py ──► data/reports/backtests/ (CSV + JSON + SVG + MD)
        ├──► scripts/run_walk_forward.py ──► data/reports/walk_forward/
        └──► scripts/run_paper_daily.py ──► data/paper/<portfolio_id>/ (state.json, equity.csv, trades.csv, latest_signal.json)
                                                   │
                                                   ▼
                                        scripts/run_dashboard.py (http://127.0.0.1:8765)
```
