# Local GUI Design

## Goal

Build a local-only research GUI for the multi-market quant framework. The GUI is for research, backtesting, status inspection, and report viewing only. It must not connect to broker APIs, place orders, or run live trading.

## Architecture

The first version uses a Python standard-library HTTP server and static HTML, CSS, and JavaScript. This keeps the app local, dependency-light, and aligned with the current Python package. The backend exposes JSON endpoints that read isolated demo fixtures and call existing research/backtest modules.

## Pages

Dashboard:
- Shows strategy count, data source readiness, latest demo research report, backtest count, and risk boundary notices.
- Labels all non-real values as demo fixture data.

Data Center:
- Shows CN, HK, US, and CRYPTO markets.
- Shows source, update time, row count, missing values, anomaly count, and status.
- Uses local demo fixture metadata only.

Factor Research:
- Provides selectors for market, universe, factor, and date range.
- Shows IC, Rank IC, ICIR, quantile group returns, and long-short returns.
- Uses demo fixture bars from `src/quant_robot/gui/fixtures/mock_data.py`.

Backtest Report:
- Shows equity curve, drawdown curve, annualized return, max drawdown, Sharpe, win rate, turnover, rebalance records, and holdings.
- Keeps labels strategy-neutral and multi-market.

Risk Monitor:
- Shows volatility, max drawdown, VaR, exposure, loss streak, and anomaly logs.
- Clearly states account data is not connected.

Logs and Reports:
- Shows research logs, backtest logs, errors, and report links.
- Provides a local button to run the demo research/backtest calculation.

## Files

Create:
- `src/quant_robot/gui/__init__.py`
- `src/quant_robot/gui/app.py`
- `src/quant_robot/gui/research_service.py`
- `src/quant_robot/gui/fixtures/__init__.py`
- `src/quant_robot/gui/fixtures/mock_data.py`
- `src/quant_robot/gui/static/index.html`
- `src/quant_robot/gui/static/styles.css`
- `src/quant_robot/gui/static/app.js`
- `scripts/run_gui.py`
- `tests/unit/test_gui.py`

Modify:
- `README.md`

## Data Boundaries

All GUI demo data lives under `src/quant_robot/gui/fixtures/`. Demo data is marked with `data_mode: demo_fixture`. The GUI does not download market data, does not read account data, and does not create order intents.

## Visual Direction

The interface should feel like a quiet professional research terminal: compact, scan-friendly, precise, and neutral. It should avoid marketing-style hero layouts and keep charts/tables readable on desktop and narrow screens.

## Testing and Verification

Unit tests cover:
- Snapshot payload includes required pages and demo labels.
- Demo research/backtest returns metrics, IC, long-short data, trades, and holdings.
- HTTP app serves HTML and JSON without external network access.

Browser verification covers:
- Local page opens.
- Navigation works for all six pages.
- Charts render non-empty SVG/canvas paths or bars.
- Desktop layout fits without overlap.
- Narrow viewport stacks panels without horizontal overflow.
