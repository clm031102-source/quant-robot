# Core Branch Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fold all surviving branch results into `main` as a clean project-core integration while preserving source traceability and keeping generated data out of Git.

**Architecture:** Work on `codex/core-branch-integration-20260618`, created from `origin/main` in an isolated worktree. Integrate the two surviving branch heads as topic groups: residual moneyflow/regime validation first, then CN ETF pipeline/research scheduling, then resolve shared core conflicts so both research lines use the same runner, Tushare ingest pipeline, technical factor layer, and tests.

**Tech Stack:** Git, PowerShell, Python 3.14 on this machine, stdlib `unittest`, `compileall`, pandas/numpy/pydantic installed into system Python for verification.

---

### Task 1: Baseline And Source Guard

**Files:**
- Read: `configs/workstations.json`
- Read: `AGENTS.md`
- Read: branch heads from `origin/main`, `origin/codex/factor-batch-cn-etf-20260617`, `origin/codex/factor-validation-long-cycle-replay-20260618`

- [x] **Step 1: Create isolated branch from `origin/main`**

Run:

```powershell
git worktree add C:\Users\Administrator\.config\superpowers\worktrees\lhjqr\codex\core-branch-integration-20260618 -b codex/core-branch-integration-20260618 origin/main
```

Expected: new worktree at `origin/main` commit `accc6f8`.

- [x] **Step 2: Install baseline dependencies for verification**

Run:

```powershell
python -m pip install -e .
```

Expected: `numpy`, `pandas`, `pydantic`, and editable `quant-robot` install succeed.

- [x] **Step 3: Run baseline tests and record failures**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_*.py'
```

Observed baseline: 482 tests run, 2 failures and 2 errors on `origin/main`; failures are in `test_experiment_runner` and `test_research_pipeline`, with date-type comparison and zero factor rows. Treat these as pre-existing baseline issues that integration should improve, not regress.

### Task 2: Integrate Residual Moneyflow / Regime Validation Core

**Files:**
- Source branch: `origin/codex/factor-validation-long-cycle-replay-20260618`
- Create/modify project files under `configs/`, `docs/`, `scripts/`, `src/quant_robot/`, and `tests/`

- [ ] **Step 1: Squash-merge residual validation branch into the integration branch**

Run:

```powershell
git merge --squash origin/codex/factor-validation-long-cycle-replay-20260618
```

Expected: clean squash merge because `git merge-tree --write-tree origin/main origin/codex/factor-validation-long-cycle-replay-20260618` exited 0.

- [ ] **Step 2: Run residual-focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_backtest tests.unit.test_desktop_factor_validation tests.unit.test_desktop_validation_summary tests.unit.test_experiment_runner tests.unit.test_factors tests.unit.test_long_cycle_replay tests.unit.test_promotion_gate tests.unit.test_research_pipeline tests.unit.test_tushare_factor_inputs_ingest tests.unit.test_tushare_moneyflow_inputs_ingest tests.unit.test_walk_forward
```

Expected: residual branch tests pass or expose concrete integration failures before commit.

- [ ] **Step 3: Commit residual validation integration**

Run:

```powershell
git add AGENTS.md README.md configs docs scripts src tests
git commit -m "feat: integrate residual regime validation core"
```

Expected: one topic commit containing residual validation workflow, promotion gate updates, long-cycle replay, startup/data manifest tools, tests, and source branch references in commit body.

### Task 3: Integrate CN ETF Pipeline And Research Scheduling

**Files:**
- Source branch: `origin/codex/factor-batch-cn-etf-20260617`
- New CN ETF modules under `src/quant_robot/assets/`, `src/quant_robot/data/ingest/`, `src/quant_robot/factors/`, `src/quant_robot/ops/`, `src/quant_robot/research/`, and `src/quant_robot/storage/`
- Shared conflict files:
  - `scripts/run_experiment_grid.py`
  - `src/quant_robot/data/ingest/tushare_pipeline.py`
  - `src/quant_robot/experiments/runner.py`
  - `src/quant_robot/factors/technical.py`
  - `tests/unit/test_tushare_ingest_pipeline.py`

- [ ] **Step 1: Start squash-merge of CN ETF branch**

Run:

```powershell
git merge --squash origin/codex/factor-batch-cn-etf-20260617
```

Expected: conflicts in the five shared files listed above because CN ETF and residual validation both extended the same core surfaces.

- [ ] **Step 2: Resolve `scripts/run_experiment_grid.py`**

Resolution rule: keep residual branch support for strict leaderboard/promotion case IDs and CN stock validation flags, and keep CN ETF branch support for factor input options used by ETF grid configs.

Verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_experiment_grid_cli tests.unit.test_experiment_runner
```

Expected: experiment grid CLI and runner tests pass.

- [ ] **Step 3: Resolve `src/quant_robot/data/ingest/tushare_pipeline.py` and `tests/unit/test_tushare_ingest_pipeline.py`**

Resolution rule: keep CN stock factor/moneyflow ingest additions from residual validation and ETF share-size/fund-portfolio ingest additions from CN ETF. The pipeline must route each dataset type explicitly and keep generated data under ignored data paths.

Verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tushare_ingest_pipeline tests.unit.test_tushare_factor_inputs_ingest tests.unit.test_tushare_moneyflow_inputs_ingest tests.unit.test_tushare_etf_share_size_ingest tests.unit.test_tushare_fund_portfolio_baskets
```

Expected: all Tushare ingest tests pass.

- [ ] **Step 4: Resolve `src/quant_robot/experiments/runner.py`**

Resolution rule: keep residual validation controls for promotion-gate-compatible case outputs and long-cycle replay, and keep CN ETF factor input/data root options. The merged runner must support both CN stock and CN ETF grids without mixed leaderboard/promotion case IDs.

Verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_experiment_runner tests.unit.test_long_cycle_replay tests.unit.test_research_family_scheduler
```

Expected: runner, long-cycle replay, and scheduler tests pass.

- [ ] **Step 5: Resolve `src/quant_robot/factors/technical.py`**

Resolution rule: preserve existing technical factors, residual validation factor additions, and CN ETF seed/diagnostic factors. Avoid renaming public factor names used by configs.

Verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_factors tests.unit.test_etf_share_size_factors tests.unit.test_etf_theme_breadth tests.unit.test_etf_moneyflow_basket_factors tests.unit.test_moneyflow_technical_combo_factors
```

Expected: factor tests pass.

- [ ] **Step 6: Commit CN ETF and shared-core integration**

Run:

```powershell
git add AGENTS.md README.md configs docs scripts src tests
git commit -m "feat: integrate cn etf pipeline and shared research core"
```

Expected: one topic commit containing CN ETF data sync, factors, readiness gate, scheduler, configs, tests, and resolved shared core.

### Task 4: Final Project-Core Verification

**Files:**
- All tracked project files except ignored/generated data.

- [ ] **Step 1: Run compile verification**

Run:

```powershell
python -m compileall -q src scripts tests
```

Expected: exit code 0.

- [ ] **Step 2: Run full unittest suite**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_*.py'
```

Expected: no failures introduced by integration. If the four baseline failures remain, document them separately; if the integrated branches fix them, report the improvement.

- [ ] **Step 3: Run repository safety audit**

Run:

```powershell
python scripts\sync_project.py --machine office_desktop --task project_sync
```

Expected: changed paths are GitHub-syncable only; no `data/raw`, `data/processed`, `data/reports`, parquet, log, token, broker, account, or order-risk files.

- [ ] **Step 4: Push integration branch**

Run:

```powershell
git push -u origin codex/core-branch-integration-20260618
```

Expected: branch pushed for review or mainline merge.

### Task 5: Update `main`

**Files:**
- Git branch state only.

- [ ] **Step 1: Move `main` only after verification**

Run after Task 4 passes or explicitly documented acceptable baseline failures:

```powershell
git switch main
git pull --ff-only origin main
git merge --ff-only codex/core-branch-integration-20260618
git push origin main
```

Expected: `main` contains the integration commits and remote `origin/main` advances.

- [ ] **Step 2: Verify final remote heads**

Run:

```powershell
git ls-remote --heads origin
```

Expected: `main`, the two source safety branches, and the integration branch until cleanup is separately approved.
