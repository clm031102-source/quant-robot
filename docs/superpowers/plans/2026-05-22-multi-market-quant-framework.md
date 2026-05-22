# Multi-Market Quant Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local phase-one Python framework for multi-market quantitative research, factor evaluation, and research backtesting without live trading.

**Architecture:** The framework uses a layered design: assets -> normalized market data -> Parquet storage -> factors -> labels -> factor evaluation -> research backtest -> reports. Data-source adapters are isolated behind interfaces so the core package runs and tests without optional live data dependencies installed.

**Tech Stack:** Python 3.11+, pandas, numpy, pydantic, optional pyarrow for Parquet, matplotlib for reports, standard-library unittest for baseline verification.

---

## File Structure

Create the following files:

```text
pyproject.toml
README.md
.env.example
configs/markets.yaml
configs/data_sources.yaml
configs/research.yaml
configs/backtest.yaml
src/quant_robot/__init__.py
src/quant_robot/assets/__init__.py
src/quant_robot/assets/models.py
src/quant_robot/assets/registry.py
src/quant_robot/assets/calendars.py
src/quant_robot/data/__init__.py
src/quant_robot/data/adapters/__init__.py
src/quant_robot/data/adapters/base.py
src/quant_robot/data/normalize.py
src/quant_robot/data/quality.py
src/quant_robot/storage/__init__.py
src/quant_robot/storage/parquet_store.py
src/quant_robot/storage/paths.py
src/quant_robot/schema/__init__.py
src/quant_robot/schema/market_data.py
src/quant_robot/schema/factors.py
src/quant_robot/factors/__init__.py
src/quant_robot/factors/technical.py
src/quant_robot/factors/pipeline.py
src/quant_robot/research/__init__.py
src/quant_robot/research/labels.py
src/quant_robot/research/ic.py
src/quant_robot/research/groups.py
src/quant_robot/research/long_short.py
src/quant_robot/backtest/__init__.py
src/quant_robot/backtest/costs.py
src/quant_robot/backtest/portfolio.py
src/quant_robot/backtest/metrics.py
src/quant_robot/backtest/engine.py
src/quant_robot/reports/__init__.py
src/quant_robot/reports/plots.py
scripts/run_fixture_research.py
tests/unit/test_assets.py
tests/unit/test_normalize.py
tests/unit/test_factors.py
tests/unit/test_labels.py
tests/unit/test_research.py
tests/unit/test_backtest.py
tests/integration/test_fixture_pipeline.py
```

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `configs/markets.yaml`
- Create: `configs/data_sources.yaml`
- Create: `configs/research.yaml`
- Create: `configs/backtest.yaml`
- Create: package `__init__.py` files listed above

- [ ] **Step 1: Write the failing import smoke test**

Create `tests/unit/test_assets.py`:

```python
from quant_robot.assets.models import Asset


def test_asset_import_smoke():
    asset = Asset(
        asset_id="US_XNAS_AAPL",
        symbol="AAPL",
        market="US",
        exchange="XNAS",
        asset_type="stock",
        currency="USD",
        timezone="America/New_York",
        calendar="XNYS",
    )

    assert asset.asset_id == "US_XNAS_AAPL"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -p "test_*.py"
```

Expected: fail because `quant_robot` or `Asset` is not defined.

- [ ] **Step 3: Create minimal project metadata and package files**

Create `pyproject.toml` with package metadata, dependencies, and setuptools configuration. Create package directories and empty `__init__.py` files. Create a concise README that states phase one excludes live trading.

- [ ] **Step 4: Run test to verify import path still fails for missing Asset**

Run the same unittest command.

Expected: fail because `quant_robot.assets.models.Asset` does not exist.

## Task 2: Asset Model And Registry

**Files:**
- Create: `src/quant_robot/assets/models.py`
- Create: `src/quant_robot/assets/registry.py`
- Create: `src/quant_robot/assets/calendars.py`
- Test: `tests/unit/test_assets.py`

- [ ] **Step 1: Extend failing tests for asset validation**

Append tests:

```python
from quant_robot.assets.registry import AssetRegistry
from quant_robot.assets.calendars import calendar_for_market


def test_asset_requires_canonical_fields():
    asset = Asset(
        asset_id="CN_XSHG_600519",
        symbol="600519",
        market="CN",
        exchange="XSHG",
        asset_type="stock",
        currency="CNY",
        timezone="Asia/Shanghai",
        calendar="XSHG",
    )

    assert asset.market == "CN"
    assert asset.timezone == "Asia/Shanghai"


def test_registry_finds_asset_by_id():
    asset = Asset(
        asset_id="CRYPTO_BINANCE_BTC_USDT",
        symbol="BTC/USDT",
        market="CRYPTO",
        exchange="BINANCE",
        asset_type="crypto_spot",
        currency="USDT",
        timezone="UTC",
        calendar="24/7",
    )
    registry = AssetRegistry([asset])

    assert registry.get("CRYPTO_BINANCE_BTC_USDT") == asset


def test_calendar_for_market_defaults():
    assert calendar_for_market("CN", "XSHG") == "XSHG"
    assert calendar_for_market("CRYPTO", "BINANCE") == "24/7"
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_assets
```

Expected: failures for missing registry and calendar functions.

- [ ] **Step 3: Implement asset model, registry, and calendar defaults**

Use a frozen dataclass for `Asset`. Reject empty canonical fields with `ValueError`. Implement `AssetRegistry.get(asset_id)` and `calendar_for_market(market, exchange)`.

- [ ] **Step 4: Run tests to verify green**

Run the same unittest command.

Expected: all asset tests pass.

## Task 3: Market Data Schema, Normalization, And Quality Checks

**Files:**
- Create: `src/quant_robot/schema/market_data.py`
- Create: `src/quant_robot/data/normalize.py`
- Create: `src/quant_robot/data/quality.py`
- Test: `tests/unit/test_normalize.py`

- [ ] **Step 1: Write failing normalization tests**

Create tests for canonical columns, UTC timestamp conversion, local date, sorting, duplicate rejection, and price consistency.

```python
import unittest
import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data


class NormalizeTests(unittest.TestCase):
    def test_normalize_adds_canonical_asset_fields_and_utc_timestamp(self):
        asset = Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")
        raw = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "open": [100.0],
                "high": [110.0],
                "low": [99.0],
                "close": [105.0],
                "volume": [1000.0],
                "amount": [105000.0],
            }
        )

        result = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")

        self.assertEqual(result.loc[0, "asset_id"], "US_XNAS_AAPL")
        self.assertEqual(str(result.loc[0, "timestamp"].tz), "UTC")
        self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")

    def test_validate_rejects_duplicate_bars(self):
        asset = Asset("CN_XSHG_600519", "600519", "CN", "XSHG", "stock", "CNY", "Asia/Shanghai", "XSHG")
        raw = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-02"],
                "open": [1.0, 1.0],
                "high": [2.0, 2.0],
                "low": [1.0, 1.0],
                "close": [1.5, 1.5],
                "volume": [10.0, 10.0],
            }
        )

        result = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")

        with self.assertRaises(ValueError):
            validate_market_data(result)
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_normalize
```

Expected: fail because normalization and validation modules do not exist.

- [ ] **Step 3: Implement schema constants, normalizer, and validators**

Implement required column lists, timezone conversion, `adj_close` fallback to `close`, `amount` optional handling, sorted output, duplicate checks, and OHLC consistency checks.

- [ ] **Step 4: Run tests to verify green**

Run the same unittest command.

Expected: normalization tests pass.

## Task 4: Parquet Storage

**Files:**
- Create: `src/quant_robot/storage/paths.py`
- Create: `src/quant_robot/storage/parquet_store.py`
- Test: `tests/unit/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create tests that verify deterministic partition paths and Parquet round-trip when `pyarrow` is installed.

```python
import importlib.util
import tempfile
import unittest
import pandas as pd

from quant_robot.storage.paths import bars_partition_path
from quant_robot.storage.parquet_store import ParquetStore


class StorageTests(unittest.TestCase):
    def test_bars_partition_path_uses_frequency_market_and_year(self):
        path = bars_partition_path("data/processed", frequency="1d", market="US", year=2024)

        self.assertEqual(path.as_posix(), "data/processed/bars/frequency=1d/market=US/year=2024")

    @unittest.skipIf(importlib.util.find_spec("pyarrow") is None, "pyarrow not installed")
    def test_parquet_store_round_trips_dataframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame = pd.DataFrame({"asset_id": ["US_XNAS_AAPL"], "market": ["US"], "year": [2024], "value": [1.0]})
            store = ParquetStore(tmp)

            store.write_dataset(frame, "sample")
            result = store.read_dataset("sample")

            self.assertEqual(result.loc[0, "asset_id"], "US_XNAS_AAPL")
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_storage
```

Expected: fail because storage modules do not exist.

- [ ] **Step 3: Implement storage paths and Parquet store**

Implement deterministic path builders. In `ParquetStore`, raise `RuntimeError("Parquet support requires pyarrow")` when neither pandas Parquet engine nor pyarrow is available.

- [ ] **Step 4: Run tests to verify green or documented skip**

Run the same unittest command.

Expected: path test passes. Round-trip test passes when `pyarrow` is installed or is skipped with a clear reason.

## Task 5: Factor Engine

**Files:**
- Create: `src/quant_robot/schema/factors.py`
- Create: `src/quant_robot/factors/technical.py`
- Create: `src/quant_robot/factors/pipeline.py`
- Test: `tests/unit/test_factors.py`

- [ ] **Step 1: Write failing factor tests**

Create tests for momentum, reversal, volatility, volume change, liquidity, and no-lookahead sentinel behavior.

```python
import unittest
import pandas as pd

from quant_robot.factors.technical import compute_basic_factors


class FactorTests(unittest.TestCase):
    def test_basic_factors_use_only_current_and_past_rows(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 6,
                "market": ["US"] * 6,
                "date": pd.date_range("2024-01-01", periods=6).date,
                "adj_close": [10.0, 11.0, 12.0, 13.0, 14.0, 1000.0],
                "close": [10.0, 11.0, 12.0, 13.0, 14.0, 1000.0],
                "volume": [100, 110, 120, 130, 140, 150],
                "amount": [1000, 1210, 1440, 1690, 1960, 150000],
            }
        )
        baseline = compute_basic_factors(bars.iloc[:5], windows=(3,))
        with_future = compute_basic_factors(bars, windows=(3,))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-01-05").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_factors
```

Expected: fail because factor functions do not exist.

- [ ] **Step 3: Implement factor calculations**

Implement per-asset rolling calculations with stable sorted output. Use `groupby("asset_id")`, `shift`, and `rolling` so future rows cannot affect earlier rows.

- [ ] **Step 4: Run tests to verify green**

Run the same unittest command.

Expected: factor tests pass.

## Task 6: Labels, IC, Group Returns, And Long-Short Returns

**Files:**
- Create: `src/quant_robot/research/labels.py`
- Create: `src/quant_robot/research/ic.py`
- Create: `src/quant_robot/research/groups.py`
- Create: `src/quant_robot/research/long_short.py`
- Test: `tests/unit/test_labels.py`
- Test: `tests/unit/test_research.py`

- [ ] **Step 1: Write failing label tests**

Test that labels use `execution_lag` and do not align same-day returns as future returns.

```python
import unittest
import pandas as pd

from quant_robot.research.labels import make_forward_returns


class LabelTests(unittest.TestCase):
    def test_forward_returns_respect_execution_lag(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 5,
                "market": ["US"] * 5,
                "date": pd.date_range("2024-01-01", periods=5).date,
                "adj_close": [100.0, 110.0, 121.0, 133.1, 146.41],
            }
        )

        labels = make_forward_returns(bars, horizons=(1,), execution_lag=1)
        first = labels[labels["date"] == pd.Timestamp("2024-01-01").date()].iloc[0]

        self.assertAlmostEqual(first["forward_return"], 0.10)
        self.assertEqual(first["entry_date"], pd.Timestamp("2024-01-02").date())
        self.assertEqual(first["exit_date"], pd.Timestamp("2024-01-03").date())
```

- [ ] **Step 2: Write failing research evaluation tests**

Test IC, Rank IC, quantile groups, and long-short output with deterministic data.

- [ ] **Step 3: Run tests to verify failures**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_labels tests.unit.test_research
```

Expected: fail because research modules do not exist.

- [ ] **Step 4: Implement labels and evaluation**

Use pandas correlation for IC. Compute Rank IC by ranking factor values and forward returns within each date before correlation. Use `pd.qcut` with deterministic fallback for small universes.

- [ ] **Step 5: Run tests to verify green**

Run the same unittest command.

Expected: label and research tests pass.

## Task 7: Research Backtest

**Files:**
- Create: `src/quant_robot/backtest/costs.py`
- Create: `src/quant_robot/backtest/portfolio.py`
- Create: `src/quant_robot/backtest/metrics.py`
- Create: `src/quant_robot/backtest/engine.py`
- Test: `tests/unit/test_backtest.py`

- [ ] **Step 1: Write failing backtest tests**

Test that signals from `t` execute after `t`, costs reduce returns, and metrics include return, volatility, Sharpe, max drawdown, and turnover.

```python
import unittest
import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest


class BacktestTests(unittest.TestCase):
    def test_backtest_executes_after_signal_date(self):
        factors = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3).date,
                "asset_id": ["A", "A", "A"],
                "market": ["US", "US", "US"],
                "factor_name": ["momentum_1", "momentum_1", "momentum_1"],
                "factor_value": [1.0, 1.0, 1.0],
            }
        )
        bars = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=4).date,
                "asset_id": ["A", "A", "A", "A"],
                "market": ["US", "US", "US", "US"],
                "adj_close": [100.0, 200.0, 220.0, 242.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0)

        self.assertEqual(result.trades.iloc[0]["signal_date"], pd.Timestamp("2024-01-01").date())
        self.assertEqual(result.trades.iloc[0]["entry_date"], pd.Timestamp("2024-01-02").date())
        self.assertGreater(result.metrics["total_return"], 0.0)
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_backtest
```

Expected: fail because backtest modules do not exist.

- [ ] **Step 3: Implement portfolio construction, costs, metrics, and engine**

Implement equal-weight top-N portfolio targets per date, next-date execution, turnover cost, daily equity curve, and metrics.

- [ ] **Step 4: Run tests to verify green**

Run the same unittest command.

Expected: backtest tests pass.

## Task 8: Fixture Pipeline And Script

**Files:**
- Create: `scripts/run_fixture_research.py`
- Create: `tests/integration/test_fixture_pipeline.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing integration test**

Test that one command-style pipeline builds assets, normalizes fixture bars, computes factors, creates labels, evaluates IC, runs a backtest, and returns metrics.

- [ ] **Step 2: Run integration test to verify failure**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.integration.test_fixture_pipeline
```

Expected: fail because the fixture pipeline script does not exist.

- [ ] **Step 3: Implement fixture pipeline**

Create deterministic fixture data for CN, HK, US, and CRYPTO inside the script. Keep the script offline and broker-free. Write report artifacts under `data/reports/fixture_research/`.

- [ ] **Step 4: Run integration test to verify green**

Run the same unittest command.

Expected: integration test passes.

## Task 9: Full Verification

**Files:**
- No new files

- [ ] **Step 1: Run all tests**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -p "test_*.py"
```

Expected: all tests pass, with Parquet round-trip skipped only if `pyarrow` is not installed.

- [ ] **Step 2: Run fixture script**

Run:

```powershell
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_fixture_research.py
```

Expected: script prints metrics and writes report files.

- [ ] **Step 3: Review no-live-trading boundary**

Run:

```powershell
rg -n "broker|order|place_order|api_key|secret|password|live" src scripts tests README.md
```

Expected: references are documentation-only or explicit non-live-trading boundary text. No real broker order implementation exists.
