# Round89 Tushare Financial Ingestion Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first reusable point-in-time Tushare financial indicator ingestion path so true CN stock profitability factors can be mined only after PIT data exists.

**Architecture:** Follow the existing Tushare ingest pattern: adapter fetches provider data, mapper normalizes provider columns, ingest writes raw and processed partitions plus manifest and quality report. This round covers `fina_indicator` first because it contains the highest-priority profitability fields and announcement dates needed for PIT discipline.

**Tech Stack:** Python, pandas, existing `DatasetStore`, existing `IngestManifest`, `unittest`, Tushare adapter abstraction.

---

### Task 1: Add Financial Indicator Mapping Contract

**Files:**
- Modify: `src/quant_robot/data/sources/tushare_mapping.py`
- Test: `tests/unit/test_tushare_mapping.py`

- [ ] **Step 1: Write the failing mapping test**

Add a test that imports `FINA_INDICATOR_COLUMNS` and `map_tushare_fina_indicator`, passes provider rows with `ts_code`, `ann_date`, `end_date`, `roe`, `roa`, `grossprofit_margin`, `netprofit_margin`, `netprofit_yoy`, `or_yoy`, `ocfps`, and `cfps`, then asserts:

```python
self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
self.assertEqual(str(result.loc[0, "ann_date"]), "2024-04-25")
self.assertEqual(str(result.loc[0, "end_date"]), "2024-03-31")
self.assertAlmostEqual(result.loc[0, "roe"], 11.2)
self.assertEqual(list(result.columns), FINA_INDICATOR_COLUMNS)
```

- [ ] **Step 2: Run the mapping test to verify RED**

Run:

```powershell
python -m unittest tests.unit.test_tushare_mapping.TushareMappingTests.test_map_fina_indicator_normalizes_pit_profitability_fields
```

Expected: import failure for `FINA_INDICATOR_COLUMNS` or `map_tushare_fina_indicator`.

- [ ] **Step 3: Implement the minimal mapper**

Add:

```python
FINA_INDICATOR_COLUMNS = [
    "symbol",
    "ann_date",
    "end_date",
    "roe",
    "roa",
    "grossprofit_margin",
    "netprofit_margin",
    "netprofit_yoy",
    "or_yoy",
    "ocfps",
    "cfps",
]
```

and `map_tushare_fina_indicator(frame)` that requires `ts_code`, `ann_date`, and `end_date`, converts dates with `%Y%m%d`, coerces numeric columns, creates missing optional profitability columns as `pd.NA`, orders columns, sorts by `symbol`, `end_date`, `ann_date`.

- [ ] **Step 4: Run the mapping tests to verify GREEN**

Run:

```powershell
python -m unittest tests.unit.test_tushare_mapping
```

Expected: all mapping tests pass.

### Task 2: Add Adapter Fetch Contract

**Files:**
- Modify: `src/quant_robot/data/adapters/tushare_adapter.py`
- Test: `tests/unit/test_tushare_adapter.py`

- [ ] **Step 1: Write the failing adapter test**

Add a fake client `fina_indicator` method and test `fetch_fina_indicator(period="20240331")`, asserting the client endpoint name, provider kwargs, mapped `symbol`, `ann_date`, and `roe`.

- [ ] **Step 2: Run the adapter test to verify RED**

Run:

```powershell
python -m unittest tests.unit.test_tushare_adapter.TushareAdapterTests.test_fetch_fina_indicator_maps_pit_profitability_fields
```

Expected: missing method on `TushareAdapter`.

- [ ] **Step 3: Implement minimal adapter method**

Add import for `map_tushare_fina_indicator` and method:

```python
def fetch_fina_indicator(self, ts_code: str = "", period: str = "", start_date: str = "", end_date: str = "") -> pd.DataFrame:
    raw = self._call(
        self.client.fina_indicator,
        ts_code=ts_code,
        period=_date_to_tushare(period) if period else "",
        start_date=_date_to_tushare(start_date) if start_date else "",
        end_date=_date_to_tushare(end_date) if end_date else "",
    )
    return map_tushare_fina_indicator(raw)
```

- [ ] **Step 4: Run the adapter tests to verify GREEN**

Run:

```powershell
python -m unittest tests.unit.test_tushare_adapter
```

Expected: all adapter tests pass.

### Task 3: Add Financial Indicator Ingest

**Files:**
- Create: `src/quant_robot/data/ingest/tushare_financial_inputs.py`
- Test: `tests/unit/test_tushare_financial_inputs_ingest.py`

- [ ] **Step 1: Write the failing ingest tests**

Create tests using a fake adapter with `fetch_fina_indicator(period)`. The first test runs periods `["20240331", "20240630"]` and asserts:

```python
self.assertEqual(result["dataset"], "fina_indicator")
self.assertEqual(result["processed_rows"], 4)
self.assertTrue((Path(tmp) / "financial_input_quality_report.json").exists())
processed = DatasetStore(Path(tmp)).read_frame(
    "processed/fina_indicator_inputs",
    {"frequency": "1q", "market": "CN", "year": "2024"},
)
self.assertIn("ann_date", processed.columns)
self.assertIn("roe", processed.columns)
self.assertEqual(set(processed["source"]), {"tushare_fina_indicator"})
```

The second test reruns with `resume=True` and asserts already completed periods are skipped.

- [ ] **Step 2: Run ingest tests to verify RED**

Run:

```powershell
python -m unittest tests.unit.test_tushare_financial_inputs_ingest
```

Expected: missing module `quant_robot.data.ingest.tushare_financial_inputs`.

- [ ] **Step 3: Implement minimal ingest module**

Implement `run_tushare_fina_indicator_ingest(adapter, periods, output_dir, resume=True, market="CN")` that:

- supports only `CN`;
- writes raw rows to `raw/tushare/fina_indicator/period=<period>`;
- normalizes to processed columns with `date = ann_date`, `asset_id`, `market`, `source`, `ingested_at`, all `FINA_INDICATOR_COLUMNS` except duplicate `symbol`;
- writes processed rows to `processed/fina_indicator_inputs/frequency=1q/market=CN/year=<ann_date year>`;
- marks manifest keys `fina_indicator:<period>`;
- writes `financial_input_quality_report.json`;
- rejects empty raw responses for requested periods.

- [ ] **Step 4: Run ingest tests to verify GREEN**

Run:

```powershell
python -m unittest tests.unit.test_tushare_financial_inputs_ingest
```

Expected: tests pass.

### Task 4: Wire CLI Fixture Source

**Files:**
- Modify: `scripts/ingest_data.py`
- Test: `tests/integration/test_ingest_cli.py`

- [ ] **Step 1: Write failing CLI fixture test**

Add a test that runs:

```python
result = run_ingest(source="tushare-fina-indicator-fixture", market="CN", output_dir=Path(tmp), start_date="2024-03-31", end_date="2024-06-30")
```

and asserts dataset `fina_indicator`, quality report exists, and processed rows are positive.

- [ ] **Step 2: Run CLI test to verify RED**

Run:

```powershell
python -m unittest tests.integration.test_ingest_cli.IngestCliTests.test_tushare_fina_indicator_fixture_ingest_writes_financial_inputs
```

Expected: unsupported source error.

- [ ] **Step 3: Implement source wiring**

Import `run_tushare_fina_indicator_ingest`, add source handlers:

- `tushare-fina-indicator-fixture`
- `tushare-fina-indicator`

Convert `start_date` and `end_date` into quarter-end periods by reusing a small helper `_quarter_end_periods(start_date, end_date)`.

- [ ] **Step 4: Run CLI tests to verify GREEN**

Run:

```powershell
python -m unittest tests.integration.test_ingest_cli
```

Expected: all CLI ingest tests pass.

### Task 5: Smoke Ingest, Readiness Audit, And Report

**Files:**
- Create: `docs/research/cn_stock_tushare_financial_ingestion_smoke_round89_2026-06-21.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Test: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Run fixture smoke ingest**

Run:

```powershell
python scripts\ingest_data.py --source tushare-fina-indicator-fixture --market CN --output-dir data\processed\tushare_fina_indicator_smoke_round89_20260621 --start-date 2024-03-31 --end-date 2024-06-30
```

Expected: writes `processed/fina_indicator_inputs` under ignored data path.

- [ ] **Step 2: Run readiness audit against smoke root**

Run:

```powershell
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\tushare_fina_indicator_smoke_round89_20260621 --output-dir data\reports\tushare_financial_pit_readiness_round89_smoke_20260621
```

Expected: `passes: true`, `financial_like_datasets > 0`, `pit_ready_datasets > 0`.

- [ ] **Step 3: Write Round89 report**

Document the fixture smoke result, fields supported, why this still is not a live data backtest, and the next direction: live Tushare small-period smoke only if token/env is configured, then long-history financial backfill.

- [ ] **Step 4: Update startup gate**

Set:

- `source_audit`: `docs/research/cn_stock_tushare_financial_ingestion_smoke_round89_2026-06-21.md`
- `next_direction`: `round90_tushare_financial_live_smoke_or_backfill`

Add confirm item `round89_tushare_financial_ingestion_smoke_read`.

- [ ] **Step 5: Verify focused tests and audit**

Run:

```powershell
python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_financial_inputs_ingest tests.integration.test_ingest_cli tests.unit.test_tushare_financial_pit_readiness tests.unit.test_tushare_financial_pit_readiness_cli tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_project_audit
python scripts\run_project_audit.py --json
git diff --check
```

Expected: tests pass, audit passes, no whitespace errors beyond line-ending warnings.

### Self-Review

Spec coverage:

- True profitability data input is addressed by `fina_indicator`.
- PIT discipline is addressed by `ann_date` and `end_date` mapping plus readiness audit.
- The plan does not mine profitability factors yet; that is intentional because live/full-history PIT data must pass before any backtest.
- No broker, account, order, or live trading actions are included.

Placeholder scan:

- No TBD or TODO placeholders.
- Every code task has an explicit test and expected RED/GREEN command.

Type consistency:

- Dataset name is consistently `fina_indicator`.
- Processed dataset path is consistently `processed/fina_indicator_inputs`.
- Source label is consistently `tushare_fina_indicator`.
