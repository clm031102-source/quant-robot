# Round157 Price-Volume Shock Reversal Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rotate away from the failed RSRS/funds-flow line by preregistering a non-RSRS CN-stock price-volume shock reversal family and forcing the next gate to be long-cycle neutral prescreening before any portfolio grid.

**Architecture:** Add one focused preregistration module that produces immutable candidate specs, JSON/Markdown/CSV outputs, and hard blockers for RSRS reuse, direct portfolio permission, and missing public-source rationale. Add a thin CLI wrapper and startup-gate config updates so every future mining run confirms the Round157 rotation before generating candidates.

**Tech Stack:** Python dataclasses, standard-library JSON/CSV writers, `unittest`, existing factor-mining startup gate config and CLI.

---

### Task 1: Round157 Preregistration Behavior

**Files:**
- Create: `tests/unit/test_price_volume_shock_reversal_preregistration.py`
- Create: `src/quant_robot/ops/price_volume_shock_reversal_preregistration.py`

- [ ] **Step 1: Write the failing test**

```python
def test_preregisters_non_rsrs_price_volume_shock_candidates_without_promotion(self) -> None:
    result = build_price_volume_shock_reversal_preregistration()
    self.assertEqual(result["stage"], "price_volume_shock_reversal_preregistration")
    self.assertTrue(result["summary"]["passes"])
    self.assertEqual(result["summary"]["candidate_count"], 8)
    self.assertGreaterEqual(result["summary"]["family_count"], 4)
    self.assertEqual(result["summary"]["rsrs_candidate_count"], 0)
    self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
    self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
    self.assertEqual(result["summary"]["next_required_gate"], "round158_price_volume_shock_reversal_neutral_prescreen")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_price_volume_shock_reversal_preregistration`

Expected: FAIL because `quant_robot.ops.price_volume_shock_reversal_preregistration` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create immutable candidate specs for exactly eight families:

```python
@dataclass(frozen=True)
class PriceVolumeShockReversalCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False
```

Use fixed candidates including Amihud liquidity shock, volume climax, range expansion exhaustion, downside volume absorption, gap-range failure, VWAP proxy reclaim, liquidity-stress normalization, and post-shock volatility compression.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_price_volume_shock_reversal_preregistration`

Expected: PASS.

### Task 2: Output Writer And CLI

**Files:**
- Modify: `tests/unit/test_price_volume_shock_reversal_preregistration.py`
- Create: `tests/unit/test_price_volume_shock_reversal_preregistration_cli.py`
- Create: `scripts/run_price_volume_shock_reversal_preregistration.py`

- [ ] **Step 1: Write failing writer and CLI tests**

```python
def test_write_outputs(self) -> None:
    result = build_price_volume_shock_reversal_preregistration()
    with tempfile.TemporaryDirectory() as tmp:
        write_price_volume_shock_reversal_preregistration(tmp, result)
        self.assertTrue((Path(tmp) / "price_volume_shock_reversal_preregistration.json").exists())
        self.assertTrue((Path(tmp) / "price_volume_shock_reversal_preregistration.md").exists())
        self.assertTrue((Path(tmp) / "price_volume_shock_reversal_candidates.csv").exists())
```

```python
def test_cli_writes_round157_outputs(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_price_volume_shock_reversal_preregistration_cli(output_dir=tmp)
        self.assertTrue(result["summary"]["passes"])
        self.assertTrue((Path(tmp) / "price_volume_shock_reversal_preregistration.json").exists())
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.unit.test_price_volume_shock_reversal_preregistration tests.unit.test_price_volume_shock_reversal_preregistration_cli`

Expected: FAIL until the CLI exists.

- [ ] **Step 3: Implement writer and CLI**

Write JSON without embedded Markdown, Markdown with candidate table and gate interpretation, CSV with factor metadata, and a CLI that prints summary JSON. The CLI must raise on preregistration blockers.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.unit.test_price_volume_shock_reversal_preregistration tests.unit.test_price_volume_shock_reversal_preregistration_cli`

Expected: PASS.

### Task 3: Startup Gate Rotation

**Files:**
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`
- Create: `docs/research/cn_stock_price_volume_shock_reversal_preregistration_round157_2026-06-23.md`

- [ ] **Step 1: Write failing startup-gate expectations**

Update the unit test to expect:

```python
self.assertEqual(
    packet["repeatable_mining_protocol"]["next_direction"],
    "round158_price_volume_shock_reversal_neutral_prescreen",
)
self.assertEqual(
    packet["repeatable_mining_protocol"]["source_audit"],
    "docs/research/cn_stock_price_volume_shock_reversal_preregistration_round157_2026-06-23.md",
)
```

Also require confirmation strings for Round157 completion, non-RSRS rotation, and no portfolio grid before neutral prescreen.

- [ ] **Step 2: Run test to verify failure**

Run: `python -m unittest tests.unit.test_factor_mining_startup_gate_cli`

Expected: FAIL because config still points to Round157 rotation from the Round154-156 review.

- [ ] **Step 3: Update config and research note**

Set `source_audit` to the Round157 research note and `next_direction` to `round158_price_volume_shock_reversal_neutral_prescreen`. Add recently rejected directions that block RSRS re-entry and price-volume portfolio grids before neutral prescreen.

- [ ] **Step 4: Run startup gate**

Run:

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\factor_mining_startup_gate_round157_post_prereg_20260623
```

Expected: exit 0 and next direction `round158_price_volume_shock_reversal_neutral_prescreen`.

### Task 4: Final Verification

**Files:**
- All files above.

- [ ] **Step 1: Run focused unit suite**

Run:

```powershell
python -m unittest tests.unit.test_price_volume_shock_reversal_preregistration tests.unit.test_price_volume_shock_reversal_preregistration_cli tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_factor_mining_startup_gate
```

Expected: PASS.

- [ ] **Step 2: Run static syntax checks**

Run:

```powershell
python -m py_compile src\quant_robot\ops\price_volume_shock_reversal_preregistration.py scripts\run_price_volume_shock_reversal_preregistration.py
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
```

Expected: both commands exit 0.

- [ ] **Step 3: Run forbidden Git path audit**

Run:

```powershell
git ls-files data/raw data/processed data/reports | Measure-Object | Select-Object -ExpandProperty Count
```

Expected: `0`.

- [ ] **Step 4: Report no commit/push**

State that commits and pushes remain disabled for this task unless the user explicitly approves.
