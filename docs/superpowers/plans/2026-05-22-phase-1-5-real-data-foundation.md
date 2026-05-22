# Phase 1.5 Real Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, offline-testable real-data foundation for Tushare A-shares, TradingView CSV verification, data quality reports, and ingestion scripts without live trading.

**Architecture:** The implementation keeps provider-specific concerns inside adapters and mappers. Tests use fake clients and local CSV fixtures so the package remains usable without Tushare, AKShare, yfinance, ccxt, pyarrow, or credentials installed.

**Tech Stack:** Python 3.11+, pandas, numpy, standard-library unittest, optional Tushare and optional Parquet engines.

---

## File Structure

Create or modify:

```text
src/quant_robot/config/__init__.py
src/quant_robot/config/secrets.py
src/quant_robot/data/adapters/tushare_adapter.py
src/quant_robot/data/adapters/tradingview_csv_adapter.py
src/quant_robot/data/sources/__init__.py
src/quant_robot/data/sources/tushare_mapping.py
src/quant_robot/data/quality_report.py
scripts/ingest_data.py
scripts/import_tradingview_csv.py
configs/universe_cn.yaml
configs/universe_crypto.yaml
configs/universe_hk.yaml
configs/universe_us.yaml
docs/phase_1_5_real_data.md
tests/unit/test_secrets.py
tests/unit/test_tushare_mapping.py
tests/unit/test_tushare_adapter.py
tests/unit/test_tradingview_csv_adapter.py
tests/unit/test_quality_report.py
tests/integration/test_ingest_cli.py
```

## Task 1: Secret Loading

**Files:**
- Create: `src/quant_robot/config/__init__.py`
- Create: `src/quant_robot/config/secrets.py`
- Test: `tests/unit/test_secrets.py`

- [ ] **Step 1: Write failing tests**

Test that environment variables load, missing required secrets raise a clear error, and `.env.example` remains blank.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_secrets
```

Expected: import failure for `quant_robot.config.secrets`.

- [ ] **Step 3: Implement minimal secret loader**

Implement `get_env_secret(name, required=False)` and `require_env_secret(name)`.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 2: Tushare Mapping

**Files:**
- Create: `src/quant_robot/data/sources/__init__.py`
- Create: `src/quant_robot/data/sources/tushare_mapping.py`
- Test: `tests/unit/test_tushare_mapping.py`

- [ ] **Step 1: Write failing mapping tests**

Test `daily`, `adj_factor`, `trade_cal`, and `stock_basic` field contracts using small dataframes.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_tushare_mapping
```

Expected: import failure.

- [ ] **Step 3: Implement mapping functions**

Implement `map_tushare_daily`, `map_tushare_adj_factor`, `map_tushare_trade_cal`, and `map_tushare_stock_basic`. Daily mapping converts volume hands to shares and amount thousand yuan to yuan.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 3: Offline-Testable Tushare Adapter

**Files:**
- Modify: `src/quant_robot/data/adapters/tushare_adapter.py`
- Test: `tests/unit/test_tushare_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Use a fake client with methods `daily`, `adj_factor`, `trade_cal`, and `stock_basic`. Test small-universe and trade-date calls.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_tushare_adapter
```

Expected: adapter missing methods.

- [ ] **Step 3: Implement adapter wrapper**

Allow dependency injection via `client=`. If no client is supplied, import Tushare lazily and load `TUSHARE_TOKEN`. Add bounded retry through a small helper.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass without Tushare installed.

## Task 4: TradingView CSV Adapter

**Files:**
- Create: `src/quant_robot/data/adapters/tradingview_csv_adapter.py`
- Create: `scripts/import_tradingview_csv.py`
- Test: `tests/unit/test_tradingview_csv_adapter.py`

- [ ] **Step 1: Write failing CSV tests**

Test common TradingView columns: `time`, `open`, `high`, `low`, `close`, `Volume`.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_tradingview_csv_adapter
```

Expected: import failure.

- [ ] **Step 3: Implement CSV parser**

Parse CSV into canonical raw OHLCV dataframe with `date`, `open`, `high`, `low`, `close`, `volume`, and optional `amount`.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 5: Data Quality Report

**Files:**
- Create: `src/quant_robot/data/quality_report.py`
- Test: `tests/unit/test_quality_report.py`

- [ ] **Step 1: Write failing quality report tests**

Test duplicate count, missing date count, zero-volume count, and coverage summary.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_quality_report
```

Expected: import failure.

- [ ] **Step 3: Implement report generator**

Return a serializable dictionary and a dataframe summary.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 6: Ingest CLI Skeleton

**Files:**
- Create: `scripts/ingest_data.py`
- Create: `configs/universe_cn.yaml`
- Create: `configs/universe_hk.yaml`
- Create: `configs/universe_us.yaml`
- Create: `configs/universe_crypto.yaml`
- Test: `tests/integration/test_ingest_cli.py`

- [ ] **Step 1: Write failing CLI integration test**

Test offline mode writes a quality report for fixture CN data.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.integration.test_ingest_cli
```

Expected: import failure for `scripts.ingest_data`.

- [ ] **Step 3: Implement offline-first CLI**

Support `--source fixture --market CN --output-dir <path>`. Live source arguments can be parsed but should fail with clear messages if dependencies or credentials are absent.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: test passes.

## Task 7: Full Verification

**Files:**
- Modify: `README.md`
- Create: `docs/phase_1_5_real_data.md`

- [ ] **Step 1: Document Phase 1.5 commands**

Add safe commands for offline ingest, TradingView CSV import, and Tushare token setup.

- [ ] **Step 2: Run all tests**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -p "test_*.py"
```

Expected: all tests pass, with Parquet round-trip skipped if no Parquet engine is installed.

- [ ] **Step 3: Run no-live-trading boundary scan**

Run:

```powershell
rg -n "broker|place_order|live trading|password|secret" src scripts tests README.md docs
```

Expected: references are boundary documentation only. No broker or real order implementation exists.
