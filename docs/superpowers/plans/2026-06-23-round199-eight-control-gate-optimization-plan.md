# Round199 Eight-Control Gate Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the CN stock candidate-plan gate so new factor mining cannot proceed without the eight user-requested controls and stricter anti-overfit requirements.

**Architecture:** Extend the existing `factor_mining_candidate_plan_gate` rather than adding a new gate. The startup and quality gates already surface the eight control areas; this plan strengthens the candidate preregistration layer by requiring stricter `promotion_policy` keys and rendering them into gate artifacts.

**Tech Stack:** Python standard library, `unittest`, existing `quant_robot.ops.factor_mining_candidate_plan_gate` module.

---

### Task 1: Promotion Policy Requirements

**Files:**
- Modify: `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`
- Test: `tests/unit/test_factor_mining_candidate_plan_gate.py`

- [ ] **Step 1: Write the failing tests**

Add tests that delete `requires_no_lookahead_audit`, `requires_final_holdout_read_once`, `requires_industry_style_neutralization`, and `requires_source_performance_evidence` from the sample candidate plan and expect `promotion_policy_missing:<key>` blockers.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
python -m unittest tests.unit.test_factor_mining_candidate_plan_gate
```

Expected before implementation: the new test fails because the gate does not require the new keys yet.

- [ ] **Step 3: Implement the minimal gate change**

Add a single `REQUIRED_PROMOTION_POLICY_KEYS` tuple in `factor_mining_candidate_plan_gate.py`, update `default_cn_stock_promotion_policy()`, and loop over the tuple inside `_blockers`.

- [ ] **Step 4: Run the focused tests and verify pass**

Run:

```powershell
python -m unittest tests.unit.test_factor_mining_candidate_plan_gate
```

Expected after implementation: all candidate-plan gate tests pass.

### Task 2: Markdown Audit Visibility

**Files:**
- Modify: `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`
- Test: `tests/unit/test_factor_mining_candidate_plan_gate.py`

- [ ] **Step 1: Write the failing test**

Add a test that renders the default packet markdown and asserts it contains `requires_no_lookahead_audit`, `requires_parameter_sensitivity`, and `requires_source_performance_evidence`.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
python -m unittest tests.unit.test_factor_mining_candidate_plan_gate
```

Expected before implementation: markdown does not show the stricter promotion policy keys.

- [ ] **Step 3: Implement the markdown section**

Add a compact `## Promotion Policy` table to `render_factor_mining_candidate_plan_gate_markdown`.

- [ ] **Step 4: Run the focused tests and verify pass**

Run:

```powershell
python -m unittest tests.unit.test_factor_mining_candidate_plan_gate
```

Expected after implementation: all candidate-plan gate tests pass.

### Task 3: Verification

**Files:**
- Validate: `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`
- Validate: `src/quant_robot/ops/factor_mining_startup.py`
- Validate: `src/quant_robot/ops/factor_mining_quality_gate.py`

- [ ] **Step 1: Run related unit tests**

```powershell
python -m unittest tests.unit.test_factor_mining_candidate_plan_gate tests.unit.test_factor_mining_startup_gate tests.unit.test_factor_mining_quality_gate tests.unit.test_factor_mining_candidate_plan_gate_cli
```

- [ ] **Step 2: Compile touched modules**

```powershell
python -m py_compile src\quant_robot\ops\factor_mining_candidate_plan_gate.py src\quant_robot\ops\factor_mining_startup.py src\quant_robot\ops\factor_mining_quality_gate.py scripts\run_factor_mining_candidate_plan_gate.py
```

- [ ] **Step 3: Run startup gate smoke**

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\round199_startup_gate_after_eight_control_optimization_20260623
```

Expected: startup gate clears for process context but direct factor generation remains blocked until quality controls and official tradeability coverage are complete.

### Commit Policy

Do not commit or push this work in this task. The user has not allowed commits/pushes for the current office desktop factor-validation session.
