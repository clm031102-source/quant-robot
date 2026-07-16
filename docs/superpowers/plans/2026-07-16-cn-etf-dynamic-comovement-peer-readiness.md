# CN ETF Dynamic Co-Movement Peer Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a fail-closed, point-in-time readiness audit for quarterly CN ETF peer sets derived from lagged market-residual return correlation.

**Architecture:** Repair the shared lifecycle loader first, then keep numerical peer construction in a pure research module and orchestration/reporting in a separate operation. A frozen config-validating CLI writes ignored machine artifacts, while only the config, tests, code, scheduler decision, and lightweight research report enter Git.

**Tech Stack:** Python 3.12, pandas, NumPy, unittest, existing DatasetStore and CN ETF eligibility utilities.

---

### Task 1: Consolidate Dated Lifecycle Snapshots

**Files:**
- Modify: `src/quant_robot/data/etf_point_in_time_universe.py`
- Modify: `tests/unit/test_etf_point_in_time_universe.py`

- [ ] **Step 1: Write the failing cross-snapshot test**

Add a test that writes two `snapshot=YYYY-MM-DD` partitions. The later row must supersede the earlier row for an overlapping symbol, while an older-only delisted ETF remains present.

```python
def test_loader_consolidates_dated_snapshots_and_preserves_older_only_assets(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_lifecycle_snapshot(root, "2026-06-21", older_rows)
        _write_lifecycle_snapshot(root, "2026-07-16", latest_rows)

        result = load_official_etf_lifecycle(root)

        self.assertEqual(set(result["symbol"]), {"510300.SH", "510500.SH"})
        self.assertTrue(result.set_index("symbol").loc["510300.SH", "is_etf"])
        self.assertEqual(
            result.set_index("symbol").loc["510500.SH", "delist_date"],
            pd.Timestamp("2024-06-28"),
        )
```

- [ ] **Step 2: Run the test and verify the current duplicate failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_etf_point_in_time_universe
```

Expected: FAIL because repeated symbols across snapshots are rejected.

- [ ] **Step 3: Implement authority-aware consolidation**

Read and normalize each file independently, reject duplicates within one source, extract a dated `snapshot=` ancestor, then keep the latest dated row per repeated symbol.

```python
def _snapshot_date_for_path(path: Path) -> pd.Timestamp | None:
    for part in reversed(path.parts):
        if part.startswith("snapshot="):
            value = pd.to_datetime(part.split("=", 1)[1], errors="coerce")
            return None if pd.isna(value) else pd.Timestamp(value).normalize()
    return None
```

Repeated symbols without distinct dated authorities must continue raising `duplicate official ETF lifecycle symbols`.

- [ ] **Step 4: Run lifecycle tests**

Run the Task 1 test command again. Expected: all tests pass.

- [ ] **Step 5: Commit the lifecycle repair**

```powershell
git add src/quant_robot/data/etf_point_in_time_universe.py tests/unit/test_etf_point_in_time_universe.py
git commit -m "fix: consolidate dated ETF lifecycle snapshots"
```

### Task 2: Build the Pure Dynamic Peer Source

**Files:**
- Create: `src/quant_robot/research/dynamic_comovement_peer_source.py`
- Create: `tests/unit/test_dynamic_comovement_peer_source.py`

- [ ] **Step 1: Write failing causality and deterministic-selection tests**

Use synthetic bars with two quarterly valid dates. Assert that every `source_end_date < valid_from`, each accepted asset has three to five peers, ties resolve by `peer_asset_id`, and appending future bars cannot change earlier mappings.

```python
policy = DynamicPeerPolicy(
    return_window=6,
    min_asset_return_observations=5,
    beta_min_observations=4,
    pair_min_observations=4,
    min_correlation=0.20,
    max_peers=3,
    min_peers=2,
)
baseline = build_dynamic_comovement_peer_source(bars, eligibility, policy=policy)
with_future = build_dynamic_comovement_peer_source(
    pd.concat([bars, future], ignore_index=True),
    pd.concat([eligibility, future_eligibility], ignore_index=True),
    policy=policy,
)
self.assert_frame_equal(
    baseline.mapping,
    with_future.mapping[with_future.mapping["valid_from"] <= cutoff].reset_index(drop=True),
)
```

- [ ] **Step 2: Run the new tests and verify import failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_dynamic_comovement_peer_source
```

Expected: ERROR because the module does not exist.

- [ ] **Step 3: Implement the frozen policy and result contract**

```python
@dataclass(frozen=True)
class DynamicPeerPolicy:
    return_window: int = 120
    min_asset_return_observations: int = 100
    market_min_cross_section: int = 30
    beta_min_observations: int = 80
    pair_min_observations: int = 80
    min_correlation: float = 0.50
    max_peers: int = 5
    min_peers: int = 3
    rebalance_months: tuple[int, ...] = (1, 4, 7, 10)


@dataclass(frozen=True)
class DynamicPeerSourceResult:
    mapping: pd.DataFrame
    snapshots: pd.DataFrame
    stability: pd.DataFrame
    duplicate_overlap: pd.DataFrame
```

Implement quarterly valid dates, lagged source windows, median market return, rolling-window OLS residuals, pairwise residual correlation, deterministic Top-K selection, directed-edge reciprocity, peer-set Jaccard/retention, and scalar-exposure nearest-neighbor overlap.

- [ ] **Step 4: Add failing interval, stability, and duplicate-evidence tests**

Assert that reversed or overlapping edge intervals cannot be emitted, consecutive peer sets produce expected Jaccard and retention values, and a topology copied from scalar beta neighbors has overlap 1.0.

- [ ] **Step 5: Implement the minimum diagnostics and rerun tests**

Run the Task 2 command. Expected: all tests pass.

- [ ] **Step 6: Commit the pure source module**

```powershell
git add src/quant_robot/research/dynamic_comovement_peer_source.py tests/unit/test_dynamic_comovement_peer_source.py
git commit -m "feat: build lagged CN ETF dynamic peer source"
```

### Task 3: Add the Fail-Closed Readiness Operation

**Files:**
- Create: `src/quant_robot/ops/cn_etf_dynamic_comovement_peer_readiness.py`
- Create: `tests/unit/test_cn_etf_dynamic_comovement_peer_readiness.py`

- [ ] **Step 1: Write failing gate tests**

Create compact synthetic source outputs for one ready case and separate failures for leakage, date coverage, stability, reciprocity, and source-duplicate overlap.

```python
result = summarize_cn_etf_dynamic_comovement_peer_readiness(
    calendar_dates=calendar,
    source=ready_source,
    min_qualifying_assets_per_date=30,
    min_qualifying_date_coverage=0.80,
    min_median_jaccard=0.25,
    min_median_retention=0.40,
    max_complete_churn_rate=0.40,
    min_reciprocity_rate=0.30,
    max_reference_edge_overlap=0.50,
    min_reference_edge_coverage=0.80,
)
self.assertEqual(result["status"], "ready_for_peer_source_preregistration")
self.assertFalse(result["factor_generation_allowed"])
```

- [ ] **Step 2: Run and verify import failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cn_etf_dynamic_comovement_peer_readiness
```

Expected: ERROR because the operation does not exist.

- [ ] **Step 3: Implement loading, gates, and artifact writing**

The builder must load bars only through 2024-06-28, consolidate lifecycle snapshots, build source-through-date eligibility with `min_prior_observations=120`, call Task 2, and return sanitized JSON-compatible output.

Write these ignored artifacts:

```python
ARTIFACT_NAMES = {
    "json": "cn_etf_dynamic_comovement_peer_readiness.json",
    "markdown": "cn_etf_dynamic_comovement_peer_readiness.md",
    "mapping_csv": "dynamic_peer_mapping.csv",
    "snapshots_csv": "snapshot_summary.csv",
    "coverage_csv": "coverage_by_date.csv",
    "stability_csv": "stability_by_transition.csv",
    "duplicate_csv": "duplicate_overlap.csv",
}
```

- [ ] **Step 4: Run operation tests**

Run the Task 3 command. Expected: all tests pass.

- [ ] **Step 5: Commit the readiness operation**

```powershell
git add src/quant_robot/ops/cn_etf_dynamic_comovement_peer_readiness.py tests/unit/test_cn_etf_dynamic_comovement_peer_readiness.py
git commit -m "feat: gate CN ETF dynamic peer readiness"
```

### Task 4: Freeze the Config And CLI

**Files:**
- Create: `configs/cn_etf_dynamic_comovement_peer_readiness_20260716.json`
- Create: `scripts/run_cn_etf_dynamic_comovement_peer_readiness.py`
- Create: `tests/unit/test_run_cn_etf_dynamic_comovement_peer_readiness.py`

- [ ] **Step 1: Write failing CLI validation tests**

Assert the CLI rejects a final-holdout end date, changed peer threshold, enabled current-name input, enabled factor generation, or enabled portfolio/live boundary.

```python
payload["peer_policy"]["min_correlation"] = 0.40
with self.assertRaisesRegex(ValueError, "frozen peer policy"):
    run_cn_etf_dynamic_comovement_peer_readiness_cli(config_path=config_path)
```

- [ ] **Step 2: Run and verify import failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_run_cn_etf_dynamic_comovement_peer_readiness
```

Expected: ERROR because the CLI does not exist.

- [ ] **Step 3: Implement exact config validation and the thin CLI**

The CLI must hash the config, call the operation once, write artifacts, and print only stage, status, blockers, next direction, and paths. Every execution boundary in the config must be exactly `false`.

- [ ] **Step 4: Run CLI tests**

Run the Task 4 command. Expected: all tests pass.

- [ ] **Step 5: Commit config and CLI**

```powershell
git add configs/cn_etf_dynamic_comovement_peer_readiness_20260716.json scripts/run_cn_etf_dynamic_comovement_peer_readiness.py tests/unit/test_run_cn_etf_dynamic_comovement_peer_readiness.py
git commit -m "feat: add frozen CN ETF dynamic peer audit CLI"
```

### Task 5: Run Real Evidence And Update Governance

**Files:**
- Modify: `configs/research_family_scheduler_cn_etf.json`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`
- Create: `docs/research/cn_etf_dynamic_comovement_peer_readiness_2026-07-16.md`

- [ ] **Step 1: Run the frozen real audit**

```powershell
.\.venv\Scripts\python.exe scripts/run_cn_etf_dynamic_comovement_peer_readiness.py --config configs/cn_etf_dynamic_comovement_peer_readiness_20260716.json
```

Expected: deterministic artifacts under `data/reports/cn_etf_dynamic_comovement_peer_readiness_20260716/` and no read of the 2026 holdout.

- [ ] **Step 2: Verify artifact hashes and gate evidence**

Re-run the command and require an identical result JSON SHA-256. Inspect every blocker, date-coverage denominator, transition count, duplicate reference, and leakage count before writing the decision.

- [ ] **Step 3: Update scheduler and durable report**

If all gates pass, keep budget zero and authorize only one later preregistration. If any gate fails, record `source_rejected_no_factor_batch`, keep budget zero, and rotate to a non-price source inventory. Store exact config/result hashes in the scheduler and report.

- [ ] **Step 4: Run scheduler and startup-gate tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cn_etf_volatility_scheduler_closeout tests.unit.test_quant_pm_startup_gate
```

- [ ] **Step 5: Commit governance evidence**

```powershell
git add configs/research_family_scheduler_cn_etf.json docs/research/CURRENT_RESEARCH_INDEX.md docs/research/cn_etf_dynamic_comovement_peer_readiness_2026-07-16.md
git commit -m "docs: record CN ETF dynamic peer readiness decision"
```

### Task 6: Verify The Entire Change

**Files:**
- Verify all changed files

- [ ] **Step 1: Run focused tests**

Run all Task 1-4 test modules together. Expected: all pass.

- [ ] **Step 2: Run full tests under the supported runtime**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Expected: all tests pass.

- [ ] **Step 3: Run compile, project audit, and maintainability audit**

```powershell
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
.\.venv\Scripts\python.exe scripts/run_project_audit.py --json
.\.venv\Scripts\python.exe scripts/run_maintainability_audit.py --fail-on-regression
```

Expected: compilation and project audit pass; maintainability reports no baseline regression.

- [ ] **Step 4: Verify repository boundaries**

```powershell
git diff --check
.\.venv\Scripts\python.exe scripts/sync_project.py --machine office_desktop --task factor_review
```

Expected: no whitespace error, forbidden path, credential, data artifact, or branch-discovery error.

- [ ] **Step 5: Perform final self-review and commit**

Review the complete diff for look-ahead, threshold drift, unsupported claims, and accidental data files. Commit any remaining test/report adjustments locally and do not push.
