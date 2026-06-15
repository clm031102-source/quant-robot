# Phase 4.9 Provider Remediation Review Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add fillable local review-template artifacts for provider-remediation rows.

**Architecture:** Extend the existing provider-remediation module with pure template/status helpers and extend the existing writer to emit two extra CSV artifacts. Keep readiness behavior unchanged until a later validation phase.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Pure Template Helpers

**Files:**
- Modify: `src/quant_robot/ops/provider_remediation.py`
- Test: `tests/unit/test_provider_remediation.py`

- [x] **Step 1: Write the failing test**

Import `build_review_template_rows` and `remediation_status_options`. Assert that a matrix with remediation items produces template rows like:

```python
rows = build_review_template_rows(matrix)
self.assertEqual(rows[0]["remediation_id"], "PR-tushare-dependency")
self.assertEqual(rows[0]["review_status"], "needs_review")
self.assertIn("resolved_locally", rows[0]["allowed_statuses"])
self.assertIn("review_guidance", rows[0])
```

Assert that `remediation_status_options()` includes `needs_review` as blocking and `resolved_locally` as non-blocking.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation
```

Expected: FAIL because the helper functions do not exist.

- [x] **Step 3: Write minimal implementation**

Add `VALID_REMEDIATION_STATUSES`, `BLOCKING_REMEDIATION_STATUSES`, `build_review_template_rows(matrix)`, and `remediation_status_options()`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation
```

Expected: PASS.

### Task 2: Writer and CLI Artifacts

**Files:**
- Modify: `src/quant_robot/ops/provider_remediation.py`
- Test: `tests/unit/test_provider_remediation_cli.py`

- [x] **Step 1: Write the failing test**

Assert that `run_provider_remediation(...)` writes:

```text
provider_remediation_review_template.csv
provider_remediation_status_options.csv
```

Also assert that the review template contains `needs_review` and the status-options file contains `resolved_locally`.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_cli
```

Expected: FAIL because the new CSV files are not written.

- [x] **Step 3: Write minimal implementation**

Update `write_provider_remediation_matrix()` to write:

```python
pd.DataFrame(build_review_template_rows(matrix)).to_csv(output_path / "provider_remediation_review_template.csv", index=False)
pd.DataFrame(remediation_status_options()).to_csv(output_path / "provider_remediation_status_options.csv", index=False)
```

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_cli
```

Expected: PASS.

### Task 3: Documentation and Real Artifact Refresh

**Files:**
- Create: `docs/phase_4_9_provider_remediation_review_template.md`
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Document the phase**

Document the CLI command, new CSV artifacts, and status interpretation.

- [x] **Step 2: Regenerate real provider remediation artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

Expected: the output directory includes `provider_remediation_review_template.csv` and `provider_remediation_status_options.csv`.

- [x] **Step 3: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_checks.py --execute
git diff --check
```

Expected: PASS except known CRLF warnings from Git on this workspace.
