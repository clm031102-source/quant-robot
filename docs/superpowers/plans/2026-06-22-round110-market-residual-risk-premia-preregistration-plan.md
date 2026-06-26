# Round110 Market Residual Risk Premia Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pre-register CN stock market-residual risk premia candidates without treating beta-adjusted hypotheses as promotion evidence.

**Architecture:** Reuse the shared capacity-safe preregistration builder and candidate dataclass. Add a focused Round110 module and CLI, then update startup-gate config to point to Round111 residual prescreen.

**Tech Stack:** Python, unittest, existing `quant_robot.ops.capacity_safe_price_volume_preregistration`, JSON/Markdown/CSV reports.

---

## File Map

- Create: `src/quant_robot/ops/market_residual_risk_premia_preregistration.py`
  - Defines Round110 candidate specs.
  - Builds preregistration output using the shared capacity-safe preregistration builder.
  - Writes Round110 JSON, Markdown, and CSV.
- Create: `scripts/run_market_residual_risk_premia_preregistration.py`
  - CLI wrapper for Round110 preregistration.
- Create: `tests/unit/test_market_residual_risk_premia_preregistration.py`
  - Tests candidate list and preregistration semantics.
- Create: `tests/unit/test_market_residual_risk_premia_preregistration_cli.py`
  - Tests CLI report output.
- Create: `docs/research/cn_stock_market_residual_risk_premia_preregistration_round110_2026-06-22.md`
  - Round110 research report.
- Modify: `configs/factor_mining_startup_cn_stock.json`
  - Advance `source_audit` and `next_direction`.
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`
  - Align default config assertions.

## Task 1: Write Failing Tests

- [ ] Create `tests/unit/test_market_residual_risk_premia_preregistration.py` importing:

```python
from quant_robot.ops.market_residual_risk_premia_preregistration import (
    ROUND107_109_SOURCE_AUDIT,
    ROUND110_NEXT_DIRECTION,
    build_market_residual_risk_premia_preregistration,
    default_market_residual_risk_premia_candidate_specs,
)
```

- [ ] Assert default specs have at least eight unique candidates.
- [ ] Assert all candidates require `adj_close` and `market_equal_weight_return`.
- [ ] Assert no candidate allows portfolio backtest or promotion.
- [ ] Assert build output stage is `market_residual_risk_premia_preregistration`, includes Round107-109 source audit, and next direction is `round111_market_residual_risk_premia_prescreen`.
- [ ] Create `tests/unit/test_market_residual_risk_premia_preregistration_cli.py` importing:

```python
from scripts.run_market_residual_risk_premia_preregistration import (
    run_market_residual_risk_premia_preregistration_cli,
)
```

- [ ] Assert JSON, Markdown, and CSV are written.
- [ ] Run:

```powershell
python -m unittest tests.unit.test_market_residual_risk_premia_preregistration tests.unit.test_market_residual_risk_premia_preregistration_cli
```

Expected before implementation: import errors for the missing module and script.

## Task 2: Implement Round110 Module

- [ ] Create `src/quant_robot/ops/market_residual_risk_premia_preregistration.py`.
- [ ] Define `ROUND107_109_SOURCE_AUDIT`, `ROUND110_NEXT_DIRECTION`, `SOURCE_EVIDENCE_STATUS`, and `STAGE`.
- [ ] Return candidate specs using `CapacitySafePriceVolumeCandidateSpec`.
- [ ] Build output through `build_capacity_safe_price_volume_preregistration`.
- [ ] Add `factor_model_context`, `family_rotation_context`, and `public_reference_review` sections.
- [ ] Add writer and Markdown renderer.

## Task 3: Implement CLI

- [ ] Create `scripts/run_market_residual_risk_premia_preregistration.py`.
- [ ] Mirror prior preregistration CLIs with `--output-dir`, `--min-candidates`, and `--allow-not-ready`.
- [ ] Print summary, factor-model context, family-rotation context, and output directory.

## Task 4: Verify and Run Real Preregistration

- [ ] Run new tests:

```powershell
python -m unittest tests.unit.test_market_residual_risk_premia_preregistration tests.unit.test_market_residual_risk_premia_preregistration_cli
```

- [ ] Run real CLI:

```powershell
python scripts\run_market_residual_risk_premia_preregistration.py --output-dir data\reports\market_residual_risk_premia_preregistration_round110_20260622 --min-candidates 8
```

## Task 5: Report and Startup Gate

- [ ] Write Round110 research report with candidate table and explicit no-promotion status.
- [ ] Update startup gate:
  - `source_audit`: Round110 research report.
  - `next_direction`: `round111_market_residual_risk_premia_prescreen`.
  - add `round110_market_residual_risk_premia_preregistration_read`.
  - add `market_residual_equal_weight_proxy_registered`.
  - reject `market_residual_risk_premia_portfolio_grid_before_prescreen`.
- [ ] Update startup-gate tests for the new source audit and next direction.

## Task 6: Final Verification

- [ ] Run:

```powershell
python -m unittest tests.unit.test_market_residual_risk_premia_preregistration tests.unit.test_market_residual_risk_premia_preregistration_cli tests.unit.test_factor_mining_startup_gate_cli
```

- [ ] Run:

```powershell
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
```

- [ ] Run:

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --market CN --asset-type stock --confirm-start --output-dir data\reports\startup_gate_round110_20260622
```

- [ ] Run:

```powershell
python scripts\run_project_audit.py --json
```

- [ ] Run:

```powershell
python -m py_compile src\quant_robot\ops\market_residual_risk_premia_preregistration.py scripts\run_market_residual_risk_premia_preregistration.py
```

- [ ] Run:

```powershell
git diff --check
```

Expected: tests, config parse, startup gate, project audit, and py_compile pass. CRLF warnings from `git diff --check` are acceptable if no whitespace errors appear.

## Self-Review

- Every design requirement maps to a task.
- No portfolio backtest, promotion, or holdout use is included.
- No placeholders remain.
- Commits and pushes are intentionally omitted because current startup policy reports them disabled.
