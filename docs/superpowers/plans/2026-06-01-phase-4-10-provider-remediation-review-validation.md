# Phase 4.10 Provider Remediation Review Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate and apply local provider-remediation review rows while keeping all behavior research-only.

**Architecture:** Extend the provider-remediation builder with optional review-row validation, extend the CLI with `--review-file`, write a validation CSV, and update the readiness board to use blocking remediation counts.

**Tech Stack:** Python 3.11+, pandas, csv, unittest.

---

### Task 1: Review Validation in Provider Remediation

**Files:**
- Modify: `src/quant_robot/ops/provider_remediation.py`
- Test: `tests/unit/test_provider_remediation.py`

- [x] **Step 1: Write the failing test**

Call `build_provider_remediation_matrix(evidence, review_rows=...)` with one valid review row, one unknown `remediation_id`, one duplicate `remediation_id`, and one invalid `review_status`. Assert:

```python
self.assertEqual(matrix["review_validation"]["summary"]["applied_review_rows"], 1)
self.assertEqual(matrix["review_validation"]["summary"]["validation_errors"], 3)
self.assertEqual(matrix["summary"]["blocking_remediation_items"], 1)
self.assertFalse(items["PR-tushare-dependency"]["blocks_provider_readiness"])
self.assertEqual(items["PR-tushare-dependency"]["review_status"], "resolved_locally")
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation
```

Expected: FAIL because the builder does not accept `review_rows`.

- [x] **Step 3: Write minimal implementation**

Add review-row validation, apply valid first rows to remediation items, add `review_validation`, add summary review-status counts, and compute `blocking_remediation_items`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation
```

Expected: PASS.

### Task 2: CLI Review File and Validation CSV

**Files:**
- Modify: `scripts/run_provider_remediation.py`
- Modify: `src/quant_robot/ops/provider_remediation.py`
- Test: `tests/unit/test_provider_remediation_cli.py`

- [x] **Step 1: Write the failing test**

Create a temporary review CSV with one valid `resolved_locally` row. Pass `review_file=review_path` to `run_provider_remediation(...)`. Assert:

```python
self.assertTrue((output_dir / "provider_remediation_validation.csv").exists())
self.assertEqual(payload["review_validation"]["summary"]["applied_review_rows"], 1)
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_cli
```

Expected: FAIL because `run_provider_remediation()` does not accept `review_file`.

- [x] **Step 3: Write minimal implementation**

Add CSV reading in the CLI, add `--review-file`, pass rows to the builder, and write `provider_remediation_validation.csv` with stable columns.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_provider_remediation_cli
```

Expected: PASS.

### Task 3: Readiness Board Uses Blocking Counts

**Files:**
- Modify: `src/quant_robot/ops/pre_api_readiness_board.py`
- Test: `tests/unit/test_pre_api_readiness_board.py`

- [x] **Step 1: Write the failing test**

Build a board with `provider_remediation.summary.remediation_items=2`, `blocking_remediation_items=0`, and `blocks_api_boundary=False`. Assert the `provider_remediation` item status is `pass` and evidence includes `blocking_remediation_items=0`.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_pre_api_readiness_board
```

Expected: FAIL because the board currently blocks on total remediation item count.

- [x] **Step 3: Write minimal implementation**

Read `blocking_remediation_items` from the provider-remediation summary, include it in evidence, and block only when blocking items remain or `blocks_api_boundary` is true.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_pre_api_readiness_board
```

Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Create: `docs/phase_4_10_provider_remediation_review_validation.md`
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Document the phase**

Document `--review-file`, validation CSV, and board-clearing behavior for non-blocking review statuses.

- [x] **Step 2: Regenerate real provider remediation and readiness artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

Expected: validation CSV exists, and the current real board remains blocked because all generated provider-remediation rows default to `needs_review`.

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
