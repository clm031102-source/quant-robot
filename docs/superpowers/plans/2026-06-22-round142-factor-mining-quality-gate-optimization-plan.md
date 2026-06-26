# Round142 Factor Mining Quality Gate Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable CN stock factor-mining quality gate so every new mining run explicitly classifies real trading constraints, PIT financial timing, neutralization, ETF scope separation, portfolio construction, strict statistics, China regime, and event factors before candidate generation or promotion.

**Architecture:** Keep the existing startup gate as the entrypoint and add a focused quality-gate module that can be rendered into the startup packet. The new gate separates "classified enough to mine" from "implemented enough to promote" so planned controls are visible without pretending they are already solved.

**Tech Stack:** Python stdlib, JSON configs, `unittest`, existing `scripts/run_factor_mining_startup_gate.py` flow.

---

### Task 1: Define Quality-Gate Behavior With Tests

**Files:**
- Create: `tests/unit/test_factor_mining_quality_gate.py`
- Create: `tests/unit/test_factor_mining_quality_gate_cli.py`

- [ ] **Step 1: Write failing tests**

```python
from quant_robot.ops.factor_mining_quality_gate import (
    DEFAULT_CN_STOCK_QUALITY_AREAS,
    build_factor_mining_quality_gate,
    validate_quality_gate_for_startup,
)

def test_default_gate_contains_user_requested_areas():
    area_ids = {area["id"] for area in DEFAULT_CN_STOCK_QUALITY_AREAS}
    assert {"cn_stock_tradeability", "financial_pit_timing", "industry_style_neutralization", "etf_rotation_scope_boundary", "portfolio_construction", "strict_statistics", "china_market_regime", "event_factors"} <= area_ids
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.unit.test_factor_mining_quality_gate tests.unit.test_factor_mining_quality_gate_cli`

Expected: fails because the module and CLI do not exist yet.

### Task 2: Implement Quality Gate Module And CLI

**Files:**
- Create: `src/quant_robot/ops/factor_mining_quality_gate.py`
- Create: `scripts/run_factor_mining_quality_gate.py`
- Create: `configs/factor_mining_quality_gate_cn_stock.json`

- [ ] **Step 1: Implement default areas and status evaluation**

Implement default control groups for the eight user-requested optimization areas. Treat `implemented` as promotion-ready, `partial` and `planned` as classified-but-not-promotion-ready, and missing controls as startup blockers.

- [ ] **Step 2: Implement JSON/Markdown CLI output**

The CLI writes `factor_mining_quality_gate.json` and `.md` under an output directory, with counts of implemented, partial, planned, missing, mining blockers, and promotion blockers.

- [ ] **Step 3: Run unit tests to verify GREEN**

Run: `python -m unittest tests.unit.test_factor_mining_quality_gate tests.unit.test_factor_mining_quality_gate_cli`

Expected: all tests pass.

### Task 3: Wire Quality Gate Into Startup Gate

**Files:**
- Modify: `src/quant_robot/ops/factor_mining_startup.py`
- Modify: `scripts/run_factor_mining_startup_gate.py`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Add quality gate to startup packet**

Load quality-gate configuration from the startup config when present and include it in the packet.

- [ ] **Step 2: Add pre-run checklist and confirmation lines**

Startup markdown must show the quality gate summary so a mining run cannot start without seeing which controls remain planned or partial.

- [ ] **Step 3: Run startup gate tests**

Run: `python -m unittest tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_factor_mining_quality_gate tests.unit.test_factor_mining_quality_gate_cli`

Expected: all tests pass.

### Task 4: Verification And Report

**Files:**
- Create: `docs/research/cn_stock_factor_mining_quality_gate_round142_2026-06-22.md`

- [ ] **Step 1: Generate current gate packet**

Run: `python scripts/run_factor_mining_quality_gate.py --config configs/factor_mining_quality_gate_cn_stock.json --output-dir data/reports/factor_mining_quality_gate_round142`

- [ ] **Step 2: Generate startup packet**

Run: `python scripts/run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data/reports/factor_mining_startup_gate_round142`

- [ ] **Step 3: Write the implementation report**

Summarize which controls are implemented, partial, planned, and which ones must block promotion until actual data logic exists.
