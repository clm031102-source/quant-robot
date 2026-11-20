# Quant Robot v2 — Agent & Engineering Guidelines

## Hard Safety Boundary (Non-Negotiable)

- **Research-to-paper only**: never connect to a live broker, read real brokerage accounts, place live orders, or implement automatic live trading.
- **No secrets or data in Git**: never commit `data/`, `.env`, `TUSHARE_TOKEN`, credentials, or large Parquet/CSV files. Keep `TUSHARE_TOKEN` in local environment variables only.

## Engineering Discipline (Keep It Clean!)

- **One source of truth**: work from the main repo (`F:\lhjqr`) or a single short-lived topic branch, and delete branches/worktrees immediately after merge. Never accumulate dozens of zombie worktrees.
- **No bureaucratic deadlocks**: never build zero-budget self-locking gates, one-off hardcoded study lists, or `no_backfill` scripts that permanently brick after a transient network error. Daily jobs must retry and cleanly catch up missed trading days.
- **Keep modules concise**: keep every Python module under 800 lines (`scripts/run_project_audit.py` enforces this).
- **Use `.venv`** (Python 3.11–3.13; currently Python 3.12.13 on `office_desktop`).

## Core Commands

```powershell
# 1. Update local CN_ETF (Tushare) + US_ETF (yfinance) daily bars
.\.venv\Scripts\python.exe scripts\run_update_data.py

# 2. Run multi-year realistic backtests (exact lots, min commissions, T+1 causality, vs Buy&Hold)
.\.venv\Scripts\python.exe scripts\run_backtest.py

# 3. Run rolling out-of-sample walk-forward validation
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --market CN_ETF

# 4. Run daily paper-trading update (idempotent + auto-backfill)
.\.venv\Scripts\python.exe scripts\run_paper_daily.py

# 5. Launch local Web Dashboard (http://127.0.0.1:8765)
.\.venv\Scripts\python.exe scripts\run_dashboard.py --open

# 6. Run full test + compile + safety audit suite
.\.venv\Scripts\python.exe scripts\run_checks.py
```
