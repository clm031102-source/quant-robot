# Tushare Ingest Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a testable Tushare A-share ingest pipeline that can plan requests, skip completed raw partitions, persist raw and processed data, and produce quality reports.

**Architecture:** The pipeline separates planning, persistence, and normalization. Tests use a fake Tushare adapter and CSV fallback storage so the implementation works without network, Tushare credentials, or a Parquet engine.

**Tech Stack:** Python 3.11+, pandas, standard-library unittest, optional Parquet engines through the existing `ParquetStore`.

---

## File Structure

Create or modify:

```text
src/quant_robot/data/ingest/__init__.py
src/quant_robot/data/ingest/manifest.py
src/quant_robot/data/ingest/tushare_pipeline.py
src/quant_robot/storage/dataset_store.py
scripts/ingest_data.py
docs/phase_1_5_real_data.md
tests/unit/test_dataset_store.py
tests/unit/test_ingest_manifest.py
tests/unit/test_tushare_ingest_pipeline.py
tests/integration/test_ingest_cli.py
```

## Task 1: Dataset Store

**Files:**
- Create: `src/quant_robot/storage/dataset_store.py`
- Test: `tests/unit/test_dataset_store.py`

- [ ] **Step 1: Write failing tests**

Test that `DatasetStore.write_frame()` writes CSV when no Parquet engine is available and `DatasetStore.exists()` detects existing partitions.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_dataset_store
```

Expected: import failure.

- [ ] **Step 3: Implement minimal store**

Implement deterministic partition directories and use CSV fallback when Parquet support is not installed.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 2: Ingest Manifest

**Files:**
- Create: `src/quant_robot/data/ingest/__init__.py`
- Create: `src/quant_robot/data/ingest/manifest.py`
- Test: `tests/unit/test_ingest_manifest.py`

- [ ] **Step 1: Write failing tests**

Test recording completed partitions, loading existing manifests, and deciding whether a request should be skipped.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_ingest_manifest
```

Expected: import failure.

- [ ] **Step 3: Implement manifest**

Use JSON with keys `completed`, `failed`, and `metadata`.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 3: Tushare Pipeline

**Files:**
- Create: `src/quant_robot/data/ingest/tushare_pipeline.py`
- Test: `tests/unit/test_tushare_ingest_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

Use a fake adapter. Test full-market mode by trade date, resume skip, raw write, processed write, and quality report output.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.unit.test_tushare_ingest_pipeline
```

Expected: import failure.

- [ ] **Step 3: Implement pipeline**

Implement `run_tushare_daily_ingest(adapter, start_date, end_date, output_dir, resume=True)`.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 4: CLI Integration

**Files:**
- Modify: `scripts/ingest_data.py`
- Modify: `tests/integration/test_ingest_cli.py`
- Modify: `docs/phase_1_5_real_data.md`

- [ ] **Step 1: Write failing CLI test**

Extend integration test to call `run_ingest(source="tushare-fixture", market="CN", output_dir=...)`.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest tests.integration.test_ingest_cli
```

Expected: unsupported source failure.

- [ ] **Step 3: Implement fixture-backed Tushare CLI mode**

Wire `tushare-fixture` into `run_tushare_daily_ingest` with a fake adapter. Real `tushare` source should use `TushareAdapter()` and fail clearly if dependency or token is missing.

- [ ] **Step 4: Run test to verify green**

Run the same command. Expected: tests pass.

## Task 5: Full Verification

**Files:**
- No new files

- [ ] **Step 1: Run all tests**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -p "test_*.py"
```

Expected: all tests pass, with Parquet round-trip skipped only if no Parquet engine is installed.

- [ ] **Step 2: Run fixture-backed Tushare ingest**

Run:

```powershell
$env:PYTHONPATH='src'
& "C:\Users\11042\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\ingest_data.py --source tushare-fixture --market CN --output-dir data\processed\tushare_fixture
```

Expected: raw data, processed data, manifest, and quality report are written.
