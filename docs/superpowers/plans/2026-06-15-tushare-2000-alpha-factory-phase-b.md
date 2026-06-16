# Tushare 2000 Alpha Factory Phase B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Tushare `daily_basic` factor-input datasets into pre-registered factor rows and allow the existing research pipeline to evaluate them with no-lookahead enforcement.

**Architecture:** Add a focused factor builder under `quant_robot.factors` that converts normalized `processed/factor_inputs` rows into existing `FACTOR_COLUMNS`. Add a storage loader for `processed/factor_inputs`, then extend `ResearchPipelineConfig` with `factor_source`, `factor_input_root`, and `factor_input_required`. The default path remains unchanged: technical factors continue to work without factor-input datasets.

**Tech Stack:** Python 3.11+, pandas, unittest, existing `DatasetStore`, existing research pipeline, existing factor schema.

---

## File Structure

- Create `src/quant_robot/factors/tushare_inputs.py`: daily-basic factor builder.
- Create `src/quant_robot/storage/factor_inputs.py`: loader for `processed/factor_inputs`.
- Modify `src/quant_robot/research/pipeline.py`: factor source selection and no-lookahead gate.
- Modify `scripts/run_research_pipeline.py`: CLI args for factor source and factor-input root.
- Create `tests/unit/test_tushare_input_factors.py`: factor builder tests.
- Create `tests/unit/test_factor_input_loader.py`: storage loader tests.
- Modify `tests/unit/test_research_pipeline.py`: pipeline integration and no-lookahead tests.

## Task 1: Daily-Basic Factor Builder

**Files:**
- Create: `src/quant_robot/factors/tushare_inputs.py`
- Create: `tests/unit/test_tushare_input_factors.py`

- [ ] **Step 1: Write failing factor-builder tests**

Create `tests/unit/test_tushare_input_factors.py` with tests proving:

- `compute_daily_basic_factors` emits rows using `FACTOR_COLUMNS`.
- raw value factors include `turnover_rate`, `turnover_rate_f`, `volume_ratio`, and `dv_ttm`.
- inverse valuation factors treat zero and negative values as missing.
- log market-cap factors treat non-positive values as missing.

Use this input frame in the tests:

```python
pd.DataFrame(
    {
        "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
        "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
        "market": ["CN", "CN"],
        "turnover_rate": [1.0, 2.0],
        "turnover_rate_f": [1.1, 2.1],
        "volume_ratio": [0.9, 1.2],
        "pe_ttm": [10.0, 0.0],
        "pb": [2.0, -1.0],
        "ps_ttm": [5.0, 0.0],
        "dv_ttm": [3.0, 4.0],
        "total_mv": [100000.0, 0.0],
        "circ_mv": [50000.0, -1.0],
    }
)
```

- [ ] **Step 2: Run factor-builder tests to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_tushare_input_factors
```

Expected: FAIL because `quant_robot.factors.tushare_inputs` does not exist.

- [ ] **Step 3: Implement daily-basic factor builder**

Create `src/quant_robot/factors/tushare_inputs.py` with:

- `DAILY_BASIC_FACTOR_NAMES = ("turnover_rate", "turnover_rate_f", "volume_ratio", "pe_ttm_inverse", "pb_inverse", "ps_ttm_inverse", "dv_ttm", "total_mv_log", "circ_mv_log")`
- `compute_daily_basic_factors(inputs: pd.DataFrame) -> pd.DataFrame`
- helper functions for safe inverse and safe log.

The output must contain only `FACTOR_COLUMNS` and use `lookback_window=1` for all daily-basic factors.

- [ ] **Step 4: Run factor-builder tests to verify GREEN**

Run the same command from Step 2.

Expected: OK.

## Task 2: Factor-Input Storage Loader

**Files:**
- Create: `src/quant_robot/storage/factor_inputs.py`
- Create: `tests/unit/test_factor_input_loader.py`

- [ ] **Step 1: Write failing loader tests**

Create tests proving:

- `load_factor_inputs(root, "CN")` reads all `processed/factor_inputs/frequency=1d/market=CN/year=*` partitions.
- `discover_factor_input_store_roots` accepts a store root, a `processed` root, and a nested search root.
- the loader raises `FileNotFoundError` when no factor-input data exists.

Use `DatasetStore(root).write_frame(frame, "processed/factor_inputs", {"frequency": "1d", "market": "CN", "year": "2024"})`.

- [ ] **Step 2: Run loader tests to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_factor_input_loader
```

Expected: FAIL because `quant_robot.storage.factor_inputs` does not exist.

- [ ] **Step 3: Implement loader**

Create `src/quant_robot/storage/factor_inputs.py` mirroring the focused discovery behavior of `src/quant_robot/storage/processed_bars.py`, but targeting `processed/factor_inputs`.

- [ ] **Step 4: Run loader tests to verify GREEN**

Run the same command from Step 2.

Expected: OK.

## Task 3: Research Pipeline Integration

**Files:**
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `tests/unit/test_research_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

Add tests proving:

- `ResearchPipelineConfig(factor_source="tushare_daily_basic", execution_lag=0, factor_input_root=tmp)` raises `ValueError`.
- a pipeline run with `factor_source="tushare_daily_basic"`, `factor_name="pb_inverse"`, `factor_input_root=tmp`, `market="CN"`, and `execution_lag=1` produces factor rows, IC rows, and request metadata showing `factor_source`.
- `factor_input_required=True` raises `ValueError` when `factor_input_root` is missing.

Use `load_demo_market_bars()` for bars and write a matching `processed/factor_inputs` dataset with the CN assets and dates from those bars.

- [ ] **Step 2: Run targeted pipeline tests to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_research_pipeline.ResearchPipelineTests.test_pipeline_rejects_tushare_daily_basic_without_execution_lag tests.unit.test_research_pipeline.ResearchPipelineTests.test_pipeline_runs_tushare_daily_basic_factor_source tests.unit.test_research_pipeline.ResearchPipelineTests.test_pipeline_requires_factor_input_root_when_requested
```

Expected: FAIL because the config fields and factor source do not exist.

- [ ] **Step 3: Implement pipeline factor-source selection**

Modify `ResearchPipelineConfig` to add:

```python
factor_source: str = "technical"
factor_input_root: Path | None = None
factor_input_required: bool = False
```

Modify `run_research_pipeline` so:

- default `technical` behavior is unchanged;
- `tushare_daily_basic` requires `execution_lag >= 1`;
- `tushare_daily_basic` requires `factor_input_root`;
- factor inputs are loaded with `load_factor_inputs`;
- daily-basic factors are computed with `compute_daily_basic_factors`;
- `combined` concatenates technical and daily-basic factors when a factor input root is available;
- result `request` includes the new config fields and `artifact_rows` includes `factor_inputs`.

- [ ] **Step 4: Run targeted pipeline tests to verify GREEN**

Run the same command from Step 2.

Expected: OK.

## Task 4: Research CLI Args

**Files:**
- Modify: `scripts/run_research_pipeline.py`

- [ ] **Step 1: Add CLI args after pipeline tests are green**

Add:

```python
parser.add_argument("--factor-source", choices=["technical", "tushare_daily_basic", "combined"], default="technical")
parser.add_argument("--factor-input-root")
parser.add_argument("--factor-input-required", action="store_true")
```

Pass them into `ResearchPipelineConfig`.

- [ ] **Step 2: Run existing research pipeline tests**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_research_pipeline
```

Expected: OK.

## Task 5: Phase B Verification

**Files:**
- Verify all files touched in Tasks 1-4.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_tushare_input_factors tests.unit.test_factor_input_loader tests.unit.test_research_pipeline
```

Expected: OK.

- [ ] **Step 2: Run full test discovery**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
```

Expected: OK.

- [ ] **Step 3: Run compile and audit**

Run:

```powershell
python -m compileall -q src scripts tests
$env:PYTHONPATH = "src"
python scripts\run_project_audit.py --json
python scripts\check_readiness.py
```

Expected: compile and audit exit 0. Readiness may still report `TUSHARE_TOKEN is not set`.
