# Tushare 2000 Alpha Factory Phase C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a disciplined daily-basic alpha factory that evaluates all pre-registered Tushare factors, tracks the hypothesis count, applies Bonferroni correction, and exports a candidate leaderboard.

**Architecture:** Extend the existing experiment grid so daily-basic factor sources can reuse the same research pipeline and cost/capacity metrics. Add a small alpha-factory module and CLI that run the pre-registered factor family, add multiple-test adjusted p-values, and write `candidate_leaderboard.csv/json` plus a manifest. Walk-forward integration remains delegated to the existing walk-forward validator once experiment grid supports factor-input configs.

**Tech Stack:** Python 3.11+, pandas, unittest, existing `ExperimentGridConfig`, existing `ResearchPipelineConfig`, existing `DatasetStore`.

---

## File Structure

- Modify `src/quant_robot/experiments/runner.py`: add `factor_source`, `factor_input_root`, `factor_input_required` and pass them into `ResearchPipelineConfig`.
- Create `src/quant_robot/research/alpha_factory.py`: Bonferroni correction and Tushare daily-basic alpha factory runner.
- Create `scripts/run_tushare_alpha_factory.py`: CLI wrapper.
- Modify `tests/unit/test_experiment_runner.py`: experiment-grid daily-basic factor-source tests.
- Create `tests/unit/test_alpha_factory.py`: correction, leaderboard, and artifact tests.
- Create `tests/unit/test_tushare_alpha_factory_cli.py`: CLI config/fixture smoke test.

## Task 1: Experiment Grid Factor-Input Support

**Files:**
- Modify: `src/quant_robot/experiments/runner.py`
- Modify: `tests/unit/test_experiment_runner.py`

- [ ] **Step 1: Write failing tests**

Add tests proving:

- `ExperimentGridConfig(factor_source="tushare_daily_basic", factor_input_root=tmp, factor_input_required=True)` runs a daily-basic factor case.
- `load_experiment_grid_config` reads `factor_source`, `factor_input_root`, and `factor_input_required`.

- [ ] **Step 2: Run targeted experiment tests to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_experiment_runner.ExperimentRunnerTests.test_experiment_grid_runs_tushare_daily_basic_factor_source tests.unit.test_experiment_runner.ExperimentRunnerTests.test_load_experiment_grid_config_reads_factor_input_options
```

Expected: FAIL because `ExperimentGridConfig` lacks these fields.

- [ ] **Step 3: Implement experiment-grid support**

Add fields to `ExperimentGridConfig`:

```python
factor_source: str = "technical"
factor_input_root: Path | None = None
factor_input_required: bool = False
```

Parse them in `load_experiment_grid_config`, pass them into `ResearchPipelineConfig`, and include `factor_source` plus `factor_input_root` in result config metadata.

- [ ] **Step 4: Run targeted experiment tests to verify GREEN**

Run the command from Step 2. Expected: OK.

## Task 2: Alpha Factory Core

**Files:**
- Create: `src/quant_robot/research/alpha_factory.py`
- Create: `tests/unit/test_alpha_factory.py`

- [ ] **Step 1: Write failing alpha-factory tests**

Create tests proving:

- `apply_bonferroni_correction` adds `hypothesis_count`, `adjusted_ic_p_value`, and `passes_adjusted_ic_p_value`.
- `run_tushare_alpha_factory` evaluates every `DAILY_BASIC_FACTOR_NAMES` factor exactly once, exports `candidate_leaderboard.csv`, `candidate_leaderboard.json`, and `manifest.json`, and includes rejection reasons when adjusted p-value fails.

- [ ] **Step 2: Run alpha-factory tests to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_alpha_factory
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement alpha factory**

Create:

- `AlphaFactoryConfig`
- `apply_bonferroni_correction(rows, p_value_key="ic_p_value", alpha=0.05)`
- `run_tushare_alpha_factory(bars, config)`

The runner must use `ExperimentGridConfig` with `factor_source="tushare_daily_basic"` and `factor_names=DAILY_BASIC_FACTOR_NAMES`, then export candidate artifacts when `output_dir` is set.

- [ ] **Step 4: Run alpha-factory tests to verify GREEN**

Run the command from Step 2. Expected: OK.

## Task 3: Alpha Factory CLI

**Files:**
- Create: `scripts/run_tushare_alpha_factory.py`
- Create: `tests/unit/test_tushare_alpha_factory_cli.py`

- [ ] **Step 1: Write failing CLI test**

Create a test that calls a `run_alpha_factory_cli(source, data_root, market, factor_input_root, output_dir, top_n, cost_bps, execution_lag, alpha)` helper with fixture bars and a temporary factor-input root, then asserts `candidate_leaderboard.csv` exists.

- [ ] **Step 2: Run CLI test to verify RED**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_tushare_alpha_factory_cli
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement CLI wrapper**

Add CLI args for `--source`, `--data-root`, `--market`, `--factor-input-root`, `--output-dir`, `--top-n`, `--cost-bps`, `--execution-lag`, `--alpha`, and date filters. Print summary plus top candidates.

- [ ] **Step 4: Run CLI test to verify GREEN**

Run the command from Step 2. Expected: OK.

## Task 4: Phase C Verification

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.unit.test_experiment_runner tests.unit.test_alpha_factory tests.unit.test_tushare_alpha_factory_cli
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_project_audit.py --json
python scripts\check_readiness.py
```

Expected: tests, compile, and audit pass. Readiness may still report `TUSHARE_TOKEN is not set`.
