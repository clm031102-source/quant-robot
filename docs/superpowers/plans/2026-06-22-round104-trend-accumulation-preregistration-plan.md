# Round104 Trend Accumulation Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pre-register a non-low-vol-reversal CN stock trend/accumulation candidate family after Round103 rejected the Bollinger cluster as redundant.

**Architecture:** Reuse the existing capacity-safe preregistration dataclass and gate logic, but provide a new candidate-spec factory, stage name, writer, and CLI for the Round104 family. The implementation produces lightweight research artifacts only.

**Tech Stack:** Python, unittest, existing capacity-safe preregistration policy.

---

### Task 1: Operation Tests

**Files:**
- Create: `tests/unit/test_capacity_safe_trend_accumulation_preregistration.py`
- Create: `src/quant_robot/ops/capacity_safe_trend_accumulation_preregistration.py`

- [ ] **Step 1: Write failing test**

```python
def test_preregisters_non_reversal_trend_accumulation_candidates(self) -> None:
    result = build_capacity_safe_trend_accumulation_preregistration(min_candidates=8)
    self.assertEqual(result["stage"], "capacity_safe_trend_accumulation_preregistration")
    self.assertTrue(result["summary"]["passes"])
    self.assertEqual(result["summary"]["candidate_count"], 10)
    names = {candidate["factor_name"] for candidate in result["candidates"]}
    self.assertIn("volume_weighted_momentum_quality_20", names)
    self.assertIn("amount_accumulation_breakout_20_60", names)
    forbidden = ("bollinger", "rsi", "donchian", "range_contraction", "lowvol_reversal")
    self.assertFalse(any(token in name for name in names for token in forbidden))
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.unit.test_capacity_safe_trend_accumulation_preregistration`

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement candidate spec factory and build function**

Return 10 `CapacitySafePriceVolumeCandidateSpec` records, all with public references, capacity filters, no portfolio permission, and next gate set by the reused preregistration builder.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.unit.test_capacity_safe_trend_accumulation_preregistration`

Expected: tests pass.

### Task 2: CLI Tests

**Files:**
- Create: `tests/unit/test_capacity_safe_trend_accumulation_preregistration_cli.py`
- Create: `scripts/run_capacity_safe_trend_accumulation_preregistration.py`

- [ ] **Step 1: Write failing CLI test**

```python
def test_cli_writes_json_markdown_and_candidate_csv(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "output"
        result = run_capacity_safe_trend_accumulation_preregistration_cli(output_dir=output, min_candidates=8)
        self.assertTrue(result["summary"]["passes"])
        self.assertTrue((output / "capacity_safe_trend_accumulation_preregistration.json").exists())
        self.assertTrue((output / "capacity_safe_trend_accumulation_preregistration.md").exists())
        self.assertTrue((output / "capacity_safe_trend_accumulation_candidates.csv").exists())
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.unit.test_capacity_safe_trend_accumulation_preregistration_cli`

Expected: import failure because the script does not exist.

- [ ] **Step 3: Implement CLI and writer**

Follow the existing preregistration CLI pattern.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.unit.test_capacity_safe_trend_accumulation_preregistration_cli`

Expected: test passes.

### Task 3: Run Round104 and Update Gate

**Files:**
- Create: `docs/research/cn_stock_capacity_safe_trend_accumulation_preregistration_round104_2026-06-22.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Run preregistration**

Run:

```powershell
python scripts\run_capacity_safe_trend_accumulation_preregistration.py --output-dir data\reports\capacity_safe_trend_accumulation_preregistration_round104_20260622 --min-candidates 8
```

- [ ] **Step 2: Write research doc**

Record the 10 candidate names, blocked directions, and next gate.

- [ ] **Step 3: Update startup gate**

Set source audit to the Round104 research doc and next direction to `round105_capacity_safe_trend_accumulation_prescreen`.

### Task 4: Verification

Run:

```powershell
python -m unittest tests.unit.test_capacity_safe_trend_accumulation_preregistration tests.unit.test_capacity_safe_trend_accumulation_preregistration_cli tests.unit.test_factor_mining_startup_gate_cli
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --confirm-start
python scripts\run_project_audit.py --json
python -m py_compile src\quant_robot\ops\capacity_safe_trend_accumulation_preregistration.py scripts\run_capacity_safe_trend_accumulation_preregistration.py
git diff --check
```

Expected: tests pass, startup gate clears to Round105, project audit passes, py_compile exits 0, and diff check has no actionable whitespace errors beyond existing CRLF warnings.
