# Tushare Moneyflow Alpha Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Tushare moneyflow as an independent real-data factor source for alpha discovery without weakening existing live-readiness gates.

**Architecture:** Keep moneyflow separate from daily_basic at every boundary: mapping, adapter method, ingest dataset, storage loader, factor builder, research factor source, and alpha factory factor universe. Pre-register a small factor set and explicit inverse variants so multiple-testing counts stay honest.

**Tech Stack:** Python, pandas, unittest, existing DatasetStore/ResearchPipeline/ExperimentGrid/AlphaFactory.

---

### Task 1: Tushare Moneyflow Mapping And Adapter

**Files:**
- Modify: `src/quant_robot/data/sources/tushare_mapping.py`
- Modify: `src/quant_robot/data/adapters/tushare_adapter.py`
- Test: `tests/unit/test_tushare_mapping.py`
- Test: `tests/unit/test_tushare_adapter.py`

- [ ] **Step 1: Write failing mapping tests**

Add tests that `map_tushare_moneyflow()` returns stable columns for empty frames, validates `ts_code`/`trade_date`, converts dates and numeric columns, and sorts by `symbol,date`.

- [ ] **Step 2: Run mapping tests to verify RED**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tushare_mapping`
Expected: FAIL because `map_tushare_moneyflow` is missing.

- [ ] **Step 3: Implement minimal mapping**

Define `MONEYFLOW_COLUMNS`, numeric column list, and `map_tushare_moneyflow(frame)`.

- [ ] **Step 4: Write failing adapter test**

Add a fake client with `moneyflow()` and assert `fetch_moneyflow_by_trade_date("2024-01-02")` calls `trade_date="20240102"` and returns mapped columns.

- [ ] **Step 5: Implement adapter method**

Import `map_tushare_moneyflow` and add `fetch_moneyflow_by_trade_date()`.

- [ ] **Step 6: Run tests to verify GREEN**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter`
Expected: OK.

### Task 2: Moneyflow Ingest And Storage Loader

**Files:**
- Create: `src/quant_robot/data/ingest/tushare_moneyflow_inputs.py`
- Create: `src/quant_robot/storage/moneyflow_inputs.py`
- Test: `tests/unit/test_tushare_moneyflow_inputs_ingest.py`
- Test: `tests/unit/test_moneyflow_input_loader.py`

- [ ] **Step 1: Write failing ingest test**

Use a fake adapter returning mapped moneyflow rows for two trade dates. Assert raw data is written under `raw/tushare/moneyflow`, processed data under `processed/moneyflow_inputs`, manifest keys are `moneyflow:YYYYMMDD`, and quality report exists.

- [ ] **Step 2: Run ingest test to verify RED**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tushare_moneyflow_inputs_ingest`
Expected: FAIL because module is missing.

- [ ] **Step 3: Implement minimal ingest**

Mirror daily_basic ingest, but normalize moneyflow rows to `date,asset_id,symbol,market,source,ingested_at` plus moneyflow numeric fields, and write yearly partitions to `processed/moneyflow_inputs`.

- [ ] **Step 4: Write failing loader test**

Create a temporary `DatasetStore` with `processed/moneyflow_inputs/frequency=1d/market=CN/year=2024` and assert `load_moneyflow_inputs(root, "CN")` returns the rows.

- [ ] **Step 5: Implement loader**

Mirror `load_factor_inputs()` discovery paths but target `processed/moneyflow_inputs`.

- [ ] **Step 6: Run tests to verify GREEN**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tushare_moneyflow_inputs_ingest tests.unit.test_moneyflow_input_loader`
Expected: OK.

### Task 3: Moneyflow Factors And Research Source

**Files:**
- Create: `src/quant_robot/factors/tushare_moneyflow.py`
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `scripts/run_research_pipeline.py`
- Test: `tests/unit/test_tushare_moneyflow_factors.py`
- Test: `tests/unit/test_research_pipeline.py`

- [ ] **Step 1: Write failing factor tests**

Assert pre-registered factors include `net_mf_amount_ratio`, `large_order_net_amount_ratio`, `extra_large_order_net_amount_ratio`, `small_order_sell_pressure`, and inverse variants where higher raw values are expected to be adverse.

- [ ] **Step 2: Implement factor builder**

Calculate each ratio using total absolute buy/sell amount as denominator, return existing `FACTOR_COLUMNS`, and coerce invalid denominators to NaN.

- [ ] **Step 3: Write failing pipeline test**

Assert `ResearchPipelineConfig(factor_source="tushare_moneyflow", moneyflow_input_root=...)` loads moneyflow inputs and emits moneyflow factors; assert `execution_lag < 1` is rejected.

- [ ] **Step 4: Implement pipeline/CLI support**

Add `moneyflow_input_root`, supported factor source `tushare_moneyflow`, loader call, factor builder call, and CLI choices/argument.

- [ ] **Step 5: Run tests to verify GREEN**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tushare_moneyflow_factors tests.unit.test_research_pipeline`
Expected: OK.

### Task 4: Alpha Factory Moneyflow Universe

**Files:**
- Modify: `src/quant_robot/research/alpha_factory.py`
- Modify: `scripts/run_tushare_alpha_factory.py`
- Test: `tests/unit/test_alpha_factory.py`
- Test: `tests/unit/test_tushare_alpha_factory_cli.py`

- [ ] **Step 1: Write failing alpha factory test**

Assert `AlphaFactoryConfig(factor_source="tushare_moneyflow", moneyflow_input_root=...)` passes moneyflow factor names to `ExperimentGridConfig` and reports `factor_source="tushare_moneyflow"` in candidate rows.

- [ ] **Step 2: Implement alpha factory source selection**

Add `factor_source` and `moneyflow_input_root` to config, route daily_basic and moneyflow universes explicitly, and keep Bonferroni count equal to all candidate factor names.

- [ ] **Step 3: Run tests to verify GREEN**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_alpha_factory tests.unit.test_tushare_alpha_factory_cli`
Expected: OK.

### Task 5: Real Data Probe

**Files:**
- No production code expected unless tests expose a bug.

- [ ] **Step 1: Ingest 2024 moneyflow real data**

Run a bounded Tushare ingest into `data/processed/tushare_alpha_factory_gate/moneyflow_inputs`.

- [ ] **Step 2: Run moneyflow alpha factory**

Run the alpha factory with `--factor-source tushare_moneyflow`, cost and execution lag enabled, and report only paper-eligible candidates after multiple-testing correction.

- [ ] **Step 3: Run paper gate for eligible candidates**

If candidates exist, run paper batch with existing paper thresholds. If all fail, live stays blocked.
