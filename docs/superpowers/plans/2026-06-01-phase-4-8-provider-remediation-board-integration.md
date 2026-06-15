# Phase 4.8 Provider Remediation Board Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provider-remediation evidence to the pre-API readiness board so provider blockers appear in the main local blocker/action view.

**Architecture:** Extend the existing board builder with one optional payload, one readiness item, one blocker mapping, and one recommended command. Extend the CLI with a default local artifact path and explicit `--provider-remediation` input.

**Tech Stack:** Python 3.11+, pandas, unittest.

---

### Task 1: Board Builder Integration

**Files:**
- Modify: `src/quant_robot/ops/pre_api_readiness_board.py`
- Test: `tests/unit/test_pre_api_readiness_board.py`

- [x] **Step 1: Write the failing test**

Add provider-remediation evidence to `test_board_consolidates_evidence_tracks_blockers_and_actions`:

```python
provider_remediation = {
    "summary": {
        "remediation_items": 7,
        "dependency_items": 4,
        "credential_items": 1,
        "adapter_items": 1,
        "storage_items": 1,
        "blocks_api_boundary": True,
    }
}
```

Pass it to `build_pre_api_readiness_board(...)` and assert:

```python
self.assertEqual(items["provider_remediation"]["status"], "block")
self.assertIn("remediation_items=7", items["provider_remediation"]["evidence"])
self.assertIn("provider_remediation_items_open", blockers)
self.assertTrue(any("run_provider_remediation.py" in action["command"] for action in board["next_local_actions"]))
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_pre_api_readiness_board
```

Expected: FAIL because `build_pre_api_readiness_board()` does not accept or expose `provider_remediation`.

- [x] **Step 3: Write minimal implementation**

Add `provider_remediation` to the builder signature, append `_provider_remediation_item(provider_remediation)` after `_provider_item(provider_evidence)` when present, map the blocker ID to `provider_remediation_items_open`, and map the recommended command to:

```text
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_pre_api_readiness_board
```

Expected: PASS.

### Task 2: CLI Integration

**Files:**
- Modify: `scripts/run_pre_api_readiness_board.py`
- Test: `tests/unit/test_pre_api_readiness_board_cli.py`

- [x] **Step 1: Write the failing test**

Write a temporary `provider_remediation_matrix.json` with summary counts, pass `provider_remediation=provider_remediation_path` to `run_pre_api_readiness_board(...)`, and assert that the written board JSON contains the `provider_remediation` track with status `block`.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_pre_api_readiness_board_cli
```

Expected: FAIL because `run_pre_api_readiness_board()` does not accept `provider_remediation`.

- [x] **Step 3: Write minimal implementation**

Add:

```python
DEFAULT_PROVIDER_REMEDIATION = Path("data/reports/provider_remediation/provider_remediation_matrix.json")
```

Then add a `provider_remediation` function argument, a CLI `--provider-remediation` argument, and pass `_read_optional_json(provider_remediation)` into `build_pre_api_readiness_board(...)`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.unit.test_pre_api_readiness_board_cli
```

Expected: PASS.

### Task 3: Documentation and Real Artifact Refresh

**Files:**
- Create: `docs/phase_4_8_provider_remediation_board_integration.md`
- Modify: `README.md`
- Modify: `docs/roadmap_after_phase_3_0.md`

- [x] **Step 1: Document the phase**

Document the CLI command, output artifacts, blocker ID, and interpretation rule for `provider_remediation`.

- [x] **Step 2: Regenerate real readiness artifacts**

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

Expected: the board includes the `provider_remediation` track and `provider_remediation_items_open` blocker when remediation rows remain.

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
