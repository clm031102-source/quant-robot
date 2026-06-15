# Tushare 2000 Alpha Factory Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first real Tushare 2000 daily-basic data foundation: adapter, mapper, factor-input ingest dataset, fixture-backed CLI path, and verification.

**Architecture:** Extend the existing Tushare adapter and mapping layer with a single new endpoint, `daily_basic`. Add a focused ingest module that writes mapped source rows to `raw/tushare/daily_basic` and normalized research rows to `processed/factor_inputs`, using the existing `DatasetStore` and `IngestManifest` patterns. Wire a fixture path into the existing ingest CLI so the behavior can be tested without live credentials, while live Tushare runs remain gated by environment readiness.

**Tech Stack:** Python 3.11+, pandas, unittest, existing `DatasetStore`, existing Tushare adapter, PowerShell verification commands.

---

## File Structure

- Modify `src/quant_robot/data/sources/tushare_mapping.py`: add `map_tushare_daily_basic`.
- Modify `src/quant_robot/data/adapters/tushare_adapter.py`: add `fetch_daily_basic_by_trade_date`.
- Create `src/quant_robot/data/ingest/tushare_factor_inputs.py`: daily-basic ingest, normalization, manifest handling, and quality report.
- Modify `scripts/ingest_data.py`: add `tushare-factor-fixture` and `tushare-factor` sources.
- Modify `tests/unit/test_tushare_mapping.py`: mapper tests.
- Modify `tests/unit/test_tushare_adapter.py`: adapter endpoint test.
- Create `tests/unit/test_tushare_factor_inputs_ingest.py`: ingest tests.
- Modify `tests/integration/test_ingest_cli.py`: CLI fixture test.

## Task 1: Daily-Basic Mapper

**Files:**
- Modify: `src/quant_robot/data/sources/tushare_mapping.py`
- Test: `tests/unit/test_tushare_mapping.py`

- [ ] **Step 1: Write the failing mapper tests**

Add these tests to `tests/unit/test_tushare_mapping.py` and import `map_tushare_daily_basic` from `quant_robot.data.sources.tushare_mapping`.

```python
def test_map_daily_basic_normalizes_numeric_fields(self):
    source = pd.DataFrame(
        {
            "ts_code": ["000001.SZ"],
            "trade_date": ["20240102"],
            "turnover_rate": ["1.25"],
            "turnover_rate_f": ["2.50"],
            "volume_ratio": ["1.10"],
            "pe": ["8.1"],
            "pe_ttm": ["7.9"],
            "pb": ["0.8"],
            "ps": ["1.2"],
            "ps_ttm": ["1.1"],
            "dv_ratio": ["3.0"],
            "dv_ttm": ["3.2"],
            "total_share": ["1000"],
            "float_share": ["800"],
            "free_share": ["600"],
            "total_mv": ["120000"],
            "circ_mv": ["90000"],
        }
    )

    result = map_tushare_daily_basic(source)

    self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
    self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")
    self.assertAlmostEqual(result.loc[0, "turnover_rate"], 1.25)
    self.assertAlmostEqual(result.loc[0, "pe_ttm"], 7.9)
    self.assertAlmostEqual(result.loc[0, "circ_mv"], 90000.0)

def test_map_daily_basic_creates_missing_optional_columns(self):
    source = pd.DataFrame({"ts_code": ["600519.SH"], "trade_date": ["20240102"], "pb": ["5.5"]})

    result = map_tushare_daily_basic(source)

    self.assertEqual(list(result.columns), [
        "symbol",
        "date",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe",
        "pe_ttm",
        "pb",
        "ps",
        "ps_ttm",
        "dv_ratio",
        "dv_ttm",
        "total_share",
        "float_share",
        "free_share",
        "total_mv",
        "circ_mv",
    ])
    self.assertAlmostEqual(result.loc[0, "pb"], 5.5)
    self.assertTrue(pd.isna(result.loc[0, "pe_ttm"]))
```

- [ ] **Step 2: Run mapper tests to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_tushare_mapping.TushareMappingTests.test_map_daily_basic_normalizes_numeric_fields tests.unit.test_tushare_mapping.TushareMappingTests.test_map_daily_basic_creates_missing_optional_columns
```

Expected: FAIL because `map_tushare_daily_basic` does not exist.

- [ ] **Step 3: Implement the mapper**

Add the following constants and function to `src/quant_robot/data/sources/tushare_mapping.py`.

```python
DAILY_BASIC_COLUMNS = [
    "symbol",
    "date",
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio",
    "dv_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
]

_DAILY_BASIC_NUMERIC_COLUMNS = [column for column in DAILY_BASIC_COLUMNS if column not in {"symbol", "date"}]

def map_tushare_daily_basic(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame, ["ts_code", "trade_date"], "tushare daily_basic")
    source = frame.copy()
    mapped = pd.DataFrame(
        {
            "symbol": source["ts_code"],
            "date": pd.to_datetime(source["trade_date"], format="%Y%m%d").dt.date,
        }
    )
    for column in _DAILY_BASIC_NUMERIC_COLUMNS:
        mapped[column] = pd.to_numeric(source[column], errors="coerce") if column in source.columns else pd.NA
    return mapped[DAILY_BASIC_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)
```

- [ ] **Step 4: Run mapper tests to verify GREEN**

Run the same command from Step 2.

Expected: OK with both tests passing.

## Task 2: Tushare Adapter Endpoint

**Files:**
- Modify: `src/quant_robot/data/adapters/tushare_adapter.py`
- Modify: `tests/unit/test_tushare_adapter.py`

- [ ] **Step 1: Write the failing adapter test**

Add `daily_basic` to `FakeTushareClient`.

```python
def daily_basic(self, **kwargs):
    self.calls.append(("daily_basic", kwargs))
    return pd.DataFrame(
        {
            "ts_code": [kwargs.get("ts_code", "000001.SZ") or "000001.SZ"],
            "trade_date": [kwargs.get("trade_date", "20240102") or "20240102"],
            "turnover_rate": [1.25],
            "turnover_rate_f": [2.5],
            "volume_ratio": [1.1],
            "pe": [8.1],
            "pe_ttm": [7.9],
            "pb": [0.8],
            "ps": [1.2],
            "ps_ttm": [1.1],
            "dv_ratio": [3.0],
            "dv_ttm": [3.2],
            "total_share": [1000.0],
            "float_share": [800.0],
            "free_share": [600.0],
            "total_mv": [120000.0],
            "circ_mv": [90000.0],
        }
    )
```

Add this test to `TushareAdapterTests`.

```python
def test_fetch_daily_basic_by_trade_date_maps_research_inputs(self):
    client = FakeTushareClient()
    adapter = TushareAdapter(client=client)

    result = adapter.fetch_daily_basic_by_trade_date("20240102")

    self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
    self.assertEqual(result.loc[0, "date"].isoformat(), "2024-01-02")
    self.assertAlmostEqual(result.loc[0, "turnover_rate"], 1.25)
    self.assertAlmostEqual(result.loc[0, "total_mv"], 120000.0)
    self.assertEqual(client.calls[0][0], "daily_basic")
    self.assertEqual(client.calls[0][1]["trade_date"], "20240102")
```

- [ ] **Step 2: Run adapter test to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_tushare_adapter.TushareAdapterTests.test_fetch_daily_basic_by_trade_date_maps_research_inputs
```

Expected: FAIL because `TushareAdapter.fetch_daily_basic_by_trade_date` does not exist.

- [ ] **Step 3: Implement adapter endpoint**

Modify `src/quant_robot/data/adapters/tushare_adapter.py`:

```python
from quant_robot.data.sources.tushare_mapping import (
    map_tushare_adj_factor,
    map_tushare_daily,
    map_tushare_daily_basic,
    map_tushare_stock_basic,
    map_tushare_trade_cal,
)

def fetch_daily_basic_by_trade_date(self, trade_date: str) -> pd.DataFrame:
    raw = self._call(self.client.daily_basic, trade_date=_date_to_tushare(trade_date))
    return map_tushare_daily_basic(raw)
```

- [ ] **Step 4: Run adapter test to verify GREEN**

Run the same command from Step 2.

Expected: OK with the new adapter test passing.

## Task 3: Daily-Basic Factor-Input Ingest

**Files:**
- Create: `src/quant_robot/data/ingest/tushare_factor_inputs.py`
- Create: `tests/unit/test_tushare_factor_inputs_ingest.py`

- [ ] **Step 1: Write failing ingest tests**

Create `tests/unit/test_tushare_factor_inputs_ingest.py` with this content.

```python
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_factor_inputs import run_tushare_daily_basic_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareDailyBasicAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame({"exchange": ["SSE"] * len(dates), "date": dates.date, "is_open": [1] * len(dates)})

    def fetch_daily_basic_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600519.SH"],
                "date": [date, date],
                "turnover_rate": [1.0, 0.5],
                "turnover_rate_f": [1.2, 0.6],
                "volume_ratio": [1.1, 0.9],
                "pe": [8.0, 30.0],
                "pe_ttm": [7.5, 28.0],
                "pb": [0.8, 10.0],
                "ps": [1.2, 15.0],
                "ps_ttm": [1.1, 14.0],
                "dv_ratio": [3.0, 1.5],
                "dv_ttm": [3.2, 1.6],
                "total_share": [1000.0, 2000.0],
                "float_share": [800.0, 1200.0],
                "free_share": [600.0, 1000.0],
                "total_mv": [120000.0, 300000.0],
                "circ_mv": [90000.0, 200000.0],
            }
        )


class FakeInvalidDailyBasicAdapter(FakeTushareDailyBasicAdapter):
    def fetch_daily_basic_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        return pd.DataFrame({"symbol": ["BAD"], "date": [pd.Timestamp("2024-01-02").date()], "pb": [1.0]})


class TushareFactorInputsIngestTests(unittest.TestCase):
    def test_daily_basic_ingest_writes_raw_processed_manifest_and_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareDailyBasicAdapter()

            result = run_tushare_daily_basic_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertEqual(adapter.calls, ["20240102", "20240103"])
            self.assertEqual(result["source"], "tushare")
            self.assertEqual(result["dataset"], "daily_basic")
            self.assertEqual(result["processed_rows"], 4)
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "factor_input_quality_report.json").exists())
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertEqual(set(processed["asset_id"]), {"CN_XSHE_000001", "CN_XSHG_600519"})
            self.assertEqual(set(processed["source"]), {"tushare"})

    def test_daily_basic_ingest_resume_skips_completed_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_daily_basic_ingest(FakeTushareDailyBasicAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            second_adapter = FakeTushareDailyBasicAdapter()

            result = run_tushare_daily_basic_ingest(second_adapter, "2024-01-02", "2024-01-03", Path(tmp), resume=True)

            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(result["skipped_trade_dates"], ["20240102", "20240103"])
            self.assertEqual(result["processed_rows"], 4)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("daily_basic:20240102", manifest["completed"])

    def test_daily_basic_ingest_marks_failed_when_processing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_tushare_daily_basic_ingest(FakeInvalidDailyBasicAdapter(), "2024-01-02", "2024-01-02", Path(tmp))

            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("daily_basic:20240102", manifest["completed"])
            self.assertIn("daily_basic:20240102", manifest["failed"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run ingest tests to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_tushare_factor_inputs_ingest
```

Expected: FAIL because `quant_robot.data.ingest.tushare_factor_inputs` does not exist.

- [ ] **Step 3: Implement ingest module**

Create `src/quant_robot/data/ingest/tushare_factor_inputs.py` with a `TushareDailyBasicAdapter` protocol and a public `run_tushare_daily_basic_ingest(adapter, start_date, end_date, output_dir, resume=True, market="CN") -> dict[str, object]` function.

The implementation must:

- support only `market="CN"`;
- load open dates from `adapter.fetch_trade_calendar`;
- write each fetched daily-basic frame to `raw/tushare/daily_basic/trade_date=YYYYMMDD`;
- normalize all rows into `processed/factor_inputs/frequency=1d/market=CN/year=YYYY`;
- derive `asset_id` from suffixes `.SZ`, `.SH`, and `.BJ`;
- write `factor_input_quality_report.json`;
- mark manifest keys as `daily_basic:YYYYMMDD`;
- mark newly downloaded keys failed if processing raises.

- [ ] **Step 4: Run ingest tests to verify GREEN**

Run the same command from Step 2.

Expected: OK with all ingest tests passing.

## Task 4: Ingest CLI Fixture Path

**Files:**
- Modify: `scripts/ingest_data.py`
- Modify: `tests/integration/test_ingest_cli.py`

- [ ] **Step 1: Write failing CLI integration test**

Add this test to `tests/integration/test_ingest_cli.py`.

```python
def test_tushare_factor_fixture_ingest_writes_factor_inputs(self):
    with tempfile.TemporaryDirectory() as tmp:
        result = run_ingest(source="tushare-factor-fixture", market="CN", output_dir=Path(tmp))

        self.assertEqual(result["dataset"], "daily_basic")
        self.assertTrue((Path(tmp) / "manifest.json").exists())
        self.assertTrue((Path(tmp) / "factor_input_quality_report.json").exists())
        self.assertGreater(result["processed_rows"], 0)
```

- [ ] **Step 2: Run CLI test to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.integration.test_ingest_cli.IngestCliTests.test_tushare_factor_fixture_ingest_writes_factor_inputs
```

Expected: FAIL because `tushare-factor-fixture` is not a supported source.

- [ ] **Step 3: Implement CLI source routing**

Modify `scripts/ingest_data.py`:

```python
from quant_robot.data.ingest.tushare_factor_inputs import run_tushare_daily_basic_ingest

if source == "tushare-factor-fixture":
    return run_tushare_daily_basic_ingest(_FixtureTushareAdapter(), start_date, end_date, output_path, market=market)
if source == "tushare-factor":
    return run_tushare_daily_basic_ingest(TushareAdapter(), start_date, end_date, output_path, market=market)
```

Add `fetch_daily_basic_by_trade_date` to `_FixtureTushareAdapter` returning two CN rows with the normalized daily-basic columns used in Task 3.

Update the unsupported-source error message to include `tushare-factor-fixture` and `tushare-factor`.

- [ ] **Step 4: Run CLI test to verify GREEN**

Run the same command from Step 2.

Expected: OK with the CLI fixture test passing.

## Task 5: Phase A Verification

**Files:**
- Verify all files touched in Tasks 1-4.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_factor_inputs_ingest tests.integration.test_ingest_cli
```

Expected: OK.

- [ ] **Step 2: Run full unit and integration test discovery**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
```

Expected: OK.

- [ ] **Step 3: Run compile verification**

Run:

```powershell
python -m compileall -q src scripts tests
```

Expected: exit code 0.

- [ ] **Step 4: Run project audit**

Run:

```powershell
$env:PYTHONPATH = "src"
python scripts\run_project_audit.py --json
```

Expected: exit code 0. Tushare live readiness may still report missing package or token if the local environment has not been activated.

- [ ] **Step 5: Record real-data activation state**

Run:

```powershell
$env:PYTHONPATH = "src"
python scripts\check_readiness.py
```

Expected before environment activation: `tushare` reports not ready if `tushare` package or `TUSHARE_TOKEN` is missing. This does not block fake-client Phase A tests, but it blocks real-data pulls.
