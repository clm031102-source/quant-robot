# Project Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CN stock research fail closed on ambiguous data, unverifiable evidence, holdout leakage, capacity violations, and stale experiment reuse while preserving the research-to-paper boundary.

**Architecture:** Add small contract and fingerprint helpers at existing subsystem boundaries, then update active entrypoints to require those contracts. Keep compatibility behavior explicit and non-promotable; do not rewrite the research platform or add live execution.

**Tech Stack:** Python 3.11+, pandas, pathlib, hashlib, JSON/CSV, unittest/pytest, GitHub Actions.

---

### Task 1: Authoritative Bar Loading And Market Validation

**Files:**
- Modify: `src/quant_robot/storage/processed_bars.py`
- Modify: `src/quant_robot/storage/authority_bars.py`
- Modify: `src/quant_robot/data/quality.py`
- Modify: `tests/unit/test_research_pipeline.py`
- Modify: `tests/unit/test_data_fixtures.py`
- Modify: `tests/unit/test_authority_bars.py`

- [x] **Step 1: Write failing tests**

```python
def test_processed_bar_loader_rejects_multiple_recursive_store_roots():
    with self.assertRaisesRegex(ValueError, "ambiguous processed bars"):
        load_processed_bars(search_root, "CN", recursive=True)

def test_market_data_rejects_cross_source_duplicate_bar():
    duplicate = pd.concat([bars, bars.assign(source="second")], ignore_index=True)
    with self.assertRaisesRegex(ValueError, "duplicate bars"):
        validate_market_data(duplicate)

def test_market_data_rejects_out_of_order_asset_rows():
    with self.assertRaisesRegex(ValueError, "not monotonic"):
        validate_market_data(out_of_order)
```

- [x] **Step 2: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_research_pipeline.py tests/unit/test_data_fixtures.py tests/unit/test_authority_bars.py -q`

Expected: new ambiguity, duplicate, and ordering assertions fail.

- [x] **Step 3: Implement strict discovery and validation**

```python
def load_processed_bars(root, market, *, recursive=False):
    roots = discover_processed_store_roots(root, market, recursive=recursive)
    if len(roots) > 1:
        raise ValueError("ambiguous processed bars ...")
    ...

duplicate_keys = ["asset_id", "timestamp", "frequency"]
for asset_id, group in frame.groupby("asset_id", sort=False):
    if not group["timestamp"].is_monotonic_increasing:
        raise ValueError(...)
```

- [x] **Step 4: Run focused tests and verify GREEN**

- [x] **Step 5: Commit**

Commit message: `fix: require authoritative processed bars`

### Task 2: Atomic Storage And Data Fingerprints

**Files:**
- Create: `src/quant_robot/storage/atomic.py`
- Create: `src/quant_robot/storage/fingerprints.py`
- Modify: `src/quant_robot/storage/dataset_store.py`
- Modify: `src/quant_robot/storage/parquet_store.py`
- Modify: `src/quant_robot/data/ingest/manifest.py`
- Modify: `src/quant_robot/ops/cn_stock_data_manifest.py`
- Modify: `tests/unit/test_dataset_store.py`
- Modify: `tests/unit/test_storage.py`
- Modify: `tests/unit/test_ingest_manifest.py`
- Modify: `tests/unit/test_cn_stock_data_manifest.py`

- [x] **Step 1: Write failing atomicity, format-conflict, and fingerprint tests**

```python
def test_write_frame_removes_stale_alternate_format(self): ...
def test_atomic_write_preserves_existing_file_when_writer_raises(self): ...
def test_manifest_rejects_changed_source_tree_fingerprint(self): ...
```

- [x] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_dataset_store.py tests/unit/test_storage.py tests/unit/test_ingest_manifest.py tests/unit/test_cn_stock_data_manifest.py -q`

- [x] **Step 3: Implement atomic replacement and deterministic fingerprints**

```python
def atomic_write(path: Path, writer: Callable[[Path], None]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp{path.suffix}")
    try:
        writer(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def fingerprint_frame(frame: pd.DataFrame) -> str: ...
def fingerprint_dataset_root(root: Path) -> dict[str, Any]: ...
```

- [x] **Step 4: Require manifest schema and fingerprint when strict validation is requested**

- [x] **Step 5: Verify GREEN and commit**

Commit message: `fix: make research data artifacts reproducible`

### Task 3: Permission-Specific Readiness Gates

**Files:**
- Modify: `src/quant_robot/ops/factor_batch_readiness_gate.py`
- Modify: `scripts/run_experiment_grid.py`
- Modify: `tests/unit/test_factor_batch_readiness_gate.py`
- Modify: `tests/unit/test_experiment_grid_cli.py`

- [x] **Step 1: Write a failing test proving a research-ready packet cannot run a portfolio grid**

```python
with self.assertRaisesRegex(ValueError, "portfolio_grid_allowed"):
    validate_factor_batch_readiness_gate_packet(path, required_permission="portfolio_grid_allowed")
```

- [x] **Step 2: Verify RED**

- [x] **Step 3: Add `required_permission` validation and require it in the grid entrypoint**

- [x] **Step 4: Verify GREEN and commit**

Commit message: `fix: enforce readiness gate permissions`

### Task 4: Promotion Evidence Contract

**Files:**
- Modify: `src/quant_robot/promotion/gate.py`
- Modify: `configs/promotion_gate_cn_stock_price_volume_technical_20260620.json`
- Modify: `configs/promotion_gate_cn_stock_daily_basic_value_size_liquidity_20260620.json`
- Modify: `configs/promotion_gate_cn_stock_daily_basic_value_low_turnover_bucket_20260620.json`
- Modify: `tests/unit/test_promotion_gate.py`

- [x] **Step 1: Add failing tests for unknown config keys, declared audit/replay paths, missing quality evidence, non-positive paper return, and provenance mismatch**

```python
def test_load_config_rejects_unknown_requirement(): ...
def test_required_progress_and_replay_packets_block_when_missing(): ...
def test_strict_paper_identity_rejects_data_fingerprint_mismatch(): ...
```

- [x] **Step 2: Verify RED**

- [x] **Step 3: Extend `PromotionGateConfig` and fail closed on required evidence**

```python
walk_forward_progress_audit: Path | None = None
long_cycle_replay: Path | None = None
require_walk_forward_progress_audit: bool = False
require_long_cycle_replay: bool = False
require_quality_report: bool = True
require_positive_paper_return: bool = True
require_paper_provenance: bool = False
```

- [x] **Step 4: Compare full candidate identity in strict mode**

- [x] **Step 5: Verify GREEN and commit**

Commit message: `fix: enforce promotion evidence contracts`

### Task 5: Structured Quality Evidence And Real CPCV Metrics

**Files:**
- Modify: `src/quant_robot/ops/factor_mining_quality_gate.py`
- Modify: `src/quant_robot/ops/factor_statistical_reality_check.py`
- Modify: `configs/factor_mining_quality_gate_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_quality_gate.py`
- Modify: `tests/unit/test_factor_statistical_reality_check.py`

- [x] **Step 1: Add failing tests showing prose cannot clear promotion and split plans cannot satisfy CPCV**

```python
def test_implemented_control_requires_machine_verifiable_artifact_for_promotion(): ...
def test_cpcv_report_requires_split_level_realized_returns(): ...
```

- [x] **Step 2: Verify RED**

- [x] **Step 3: Validate structured control artifacts and calculate CPCV split distributions**

```python
def evaluate_purged_cpcv(frame, splits, *, date_column, return_column, case_column):
    # Return split Sharpe, positive split rate, lower quantile, and pass state per case.
    ...
```

- [x] **Step 4: Verify GREEN and commit**

Commit message: `fix: require verified statistical controls`

### Task 6: Point-In-Time And Multi-Horizon Correctness

**Files:**
- Modify: `src/quant_robot/ops/cn_stock_tradeability_gate.py`
- Modify: `src/quant_robot/ops/profitability_quality_factor_matrix_smoke.py`
- Modify: `src/quant_robot/research/ic.py`
- Modify: `src/quant_robot/research/groups.py`
- Modify: `src/quant_robot/research/long_short.py`
- Modify: `src/quant_robot/research/overlap.py`
- Modify: `src/quant_robot/research/pipeline.py`
- Modify: `tests/unit/test_cn_stock_tradeability_gate.py`
- Modify: `tests/unit/test_profitability_quality_factor_matrix_smoke.py`
- Modify: `tests/unit/test_research.py`
- Modify: `tests/unit/test_research_pipeline.py`

- [x] **Step 1: Add failing tests for pre-delist eligibility, post-announcement execution, separate horizons, and HAC evidence**

- [x] **Step 2: Verify RED**

- [x] **Step 3: Implement effective-date status logic and strict next-session event alignment**

- [x] **Step 4: Carry optional label dimensions through IC, quantile, and long-short grouping**

- [x] **Step 5: Use Newey-West mean tests with at least 20 IC observations**

- [x] **Step 6: Verify GREEN and commit**

Commit message: `fix: remove PIT and horizon mixing bias`

### Task 7: Read-Once Final Holdout Contract

**Files:**
- Create: `src/quant_robot/validation/final_holdout_access.py`
- Modify: `src/quant_robot/ops/capacity_safe_price_volume_prescreen.py`
- Modify: `scripts/run_capacity_safe_price_volume_prescreen.py`
- Modify: `tests/unit/test_capacity_safe_price_volume_prescreen.py`
- Modify: `tests/unit/test_capacity_safe_price_volume_prescreen_cli.py`

- [x] **Step 1: Add failing tests that reject a bare `include_final_holdout=True`, changed candidate hashes, and a second read**

- [x] **Step 2: Verify RED**

- [x] **Step 3: Implement frozen-candidate hash plus atomic read-once ledger receipt**

```python
def authorize_final_holdout(*, packet_path, ledger_path, candidate_hash, context) -> dict[str, Any]: ...
```

- [x] **Step 4: Replace the bare CLI flag with packet and ledger arguments**

- [x] **Step 5: Verify GREEN and commit**

Commit message: `fix: lock final holdout access`

### Task 8: Capacity, Impact, Turnover, And Walk-Forward Rejection

**Files:**
- Modify: `src/quant_robot/backtest/costs.py`
- Modify: `src/quant_robot/backtest/engine.py`
- Modify: `src/quant_robot/experiments/runner.py`
- Modify: `src/quant_robot/validation/walk_forward.py`
- Modify: `tests/unit/test_backtest.py`
- Modify: `tests/unit/test_experiment_runner.py`
- Modify: `tests/unit/test_walk_forward.py`

- [x] **Step 1: Add failing tests for missing amount, rejected over-capacity trades, uncapped impact, target-weight turnover, and downstream rejection**

- [x] **Step 2: Verify RED**

- [x] **Step 3: Reject unmeasurable/over-limit capacity and compute target-delta turnover**

- [x] **Step 4: Surface `capacity_rejected_trades` and reject affected validation cases**

- [x] **Step 5: Verify GREEN and commit**

Commit message: `fix: enforce executable capacity constraints`

### Task 9: Experiment Fingerprints And Cumulative Hypothesis Ledger

**Files:**
- Create: `src/quant_robot/research/hypothesis_ledger.py`
- Modify: `src/quant_robot/experiments/runner.py`
- Modify: `src/quant_robot/validation/walk_forward.py`
- Modify: `tests/unit/test_experiment_runner.py`
- Modify: `tests/unit/test_walk_forward.py`

- [x] **Step 1: Add failing tests showing changed bars/config/code invalidate resume and prior hypotheses increase correction count**

- [x] **Step 2: Verify RED**

- [x] **Step 3: Record config, data, code, and environment fingerprints in experiment manifests**

- [x] **Step 4: Atomically register unique tested case identities in the cumulative ledger**

- [x] **Step 5: Verify GREEN and commit**

Commit message: `fix: fingerprint experiments and track all hypotheses`

### Task 10: Fail-Closed Gap Audit

**Files:**
- Modify: `src/quant_robot/data/gap_audit.py`
- Modify: `scripts/run_data_quality_audit.py`
- Modify: `tests/unit/test_data_quality_gap_audit.py`
- Modify: `tests/unit/test_data_quality_gap_audit_cli.py`

- [ ] **Step 1: Add failing tests for missing explicit calendar, whole-market gaps, and example truncation**

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Separate total counts from examples and add decision/status fields**

- [ ] **Step 4: Add `--calendar-path` and non-zero blocked exit**

- [ ] **Step 5: Verify GREEN and commit**

Commit message: `fix: make market gap audits fail closed`

### Task 11: Repository Safety And Reproducibility

**Files:**
- Create: `.gitattributes`
- Create: `requirements/constraints-ci.txt`
- Modify: `.gitignore`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `src/quant_robot/audit/project_audit.py`
- Modify: `scripts/sync_project.py`
- Modify: `tests/unit/test_project_audit.py`
- Modify: `tests/unit/test_sync_project.py`
- Modify: `tests/unit/test_gui.py`
- Modify: `tests/unit/test_cloud_project_docs.py`

- [ ] **Step 1: Add failing tests for case-insensitive forbidden identifiers, inline safety-phrase bypass, fixture imports, secret content, risky extensions, and large files**

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement AST-aware audit and content-aware sync inspection**

- [ ] **Step 4: Add deterministic line endings, bounded dependencies, and CI matrix/build checks**

- [ ] **Step 5: Verify GREEN and commit**

Commit message: `chore: harden repository governance`

### Task 12: Honest Readiness And Maintainability Reporting

**Files:**
- Create: `scripts/run_maintainability_audit.py`
- Create: `tests/unit/test_maintainability_audit.py`
- Modify: `scripts/run_project_completion_gate.py`
- Modify: `tests/unit/test_project_completion_gate.py`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] **Step 1: Add failing tests that reject whole-project completion claims and report large-module/test-topology debt**

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Reframe completion as pre-alpha readiness and remove synthetic 98/99/100 scoring**

- [ ] **Step 4: Add non-growing maintainability baselines and correct historical documentation**

- [ ] **Step 5: Verify GREEN and commit**

Commit message: `docs: report research readiness honestly`

### Task 13: Full Verification And Audit Report Closeout

**Files:**
- Modify: `docs/superpowers/plans/2026-07-10-project-audit-remediation.md`
- Create: `docs/research/project_audit_remediation_summary_2026-07-10.md`

- [ ] **Step 1: Run focused changed-subsystem tests**

Run: `.venv\Scripts\python.exe -m pytest <all changed test files> -q`

- [ ] **Step 2: Run the complete unit suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`

- [ ] **Step 3: Run compile, project audit, and diff validation**

```powershell
.venv\Scripts\python.exe -m compileall -q src scripts tests
.venv\Scripts\python.exe scripts/run_project_audit.py --json
git diff --check
```

- [ ] **Step 4: Record exact pass/fail evidence and external blockers in the remediation summary**

- [ ] **Step 5: Commit without pushing**

Commit message: `docs: close audit remediation round`
