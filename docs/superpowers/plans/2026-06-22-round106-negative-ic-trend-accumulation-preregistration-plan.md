# Round106 Negative-IC Trend Accumulation Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pre-register anti-overheat trend/amount accumulation CN stock candidates derived from Round105 negative-IC evidence without treating inversion as promotion evidence.

**Architecture:** Reuse the existing capacity-safe preregistration builder and candidate dataclass. Add a focused Round106 module and CLI, then update startup-gate config to point to Round107 prescreen and write a Round104-106 review.

**Tech Stack:** Python, unittest, existing `quant_robot.ops.capacity_safe_price_volume_preregistration`, JSON/Markdown/CSV reports.

---

## File Map

- Create: `src/quant_robot/ops/negative_ic_trend_accumulation_preregistration.py`
  - Defines Round106 candidate specs.
  - Builds preregistration output using the shared capacity-safe preregistration builder.
  - Writes Round106 JSON, Markdown, and CSV.
- Create: `scripts/run_negative_ic_trend_accumulation_preregistration.py`
  - CLI wrapper for Round106 preregistration.
- Create: `tests/unit/test_negative_ic_trend_accumulation_preregistration.py`
  - Tests candidate list and preregistration semantics.
- Create: `tests/unit/test_negative_ic_trend_accumulation_preregistration_cli.py`
  - Tests CLI report output.
- Create: `docs/research/cn_stock_negative_ic_trend_accumulation_preregistration_round106_2026-06-22.md`
  - Round106 research report.
- Create: `docs/research/cn_stock_round104_106_three_round_review_2026-06-22.md`
  - Three-round review and direction audit.
- Modify: `configs/factor_mining_startup_cn_stock.json`
  - Advance `source_audit` and `next_direction`.
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`
  - Align default config assertions.

## Task 1: Write Failing Tests

- [ ] Add tests importing:

```python
from quant_robot.ops.negative_ic_trend_accumulation_preregistration import (
    build_negative_ic_trend_accumulation_preregistration,
    default_negative_ic_trend_accumulation_candidate_specs,
)
```

- [ ] Assert default specs have at least eight unique candidates and names include anti/overheat semantics.
- [ ] Assert no candidate allows portfolio backtest or promotion.
- [ ] Assert build output stage is `negative_ic_trend_accumulation_preregistration`, includes Round105 source evidence, and next direction is `round107_negative_ic_trend_accumulation_prescreen`.
- [ ] Add CLI test importing:

```python
from scripts.run_negative_ic_trend_accumulation_preregistration import (
    run_negative_ic_trend_accumulation_preregistration_cli,
)
```

- [ ] Assert JSON, Markdown, and CSV are written.
- [ ] Run:

```powershell
python -m unittest tests.unit.test_negative_ic_trend_accumulation_preregistration tests.unit.test_negative_ic_trend_accumulation_preregistration_cli
```

Expected before implementation: import errors for the missing module and script.

## Task 2: Implement Round106 Module

- [ ] Create `src/quant_robot/ops/negative_ic_trend_accumulation_preregistration.py`.
- [ ] Define `ROUND105_SOURCE_AUDIT`, `ROUND106_NEXT_DIRECTION`, and `STAGE`.
- [ ] Return candidate specs using `CapacitySafePriceVolumeCandidateSpec`.
- [ ] Build output through `build_capacity_safe_price_volume_preregistration`.
- [ ] Add `negative_ic_context`, `family_rotation_context`, and `public_reference_review` sections.
- [ ] Add writer and Markdown renderer.

## Task 3: Implement CLI

- [ ] Create `scripts/run_negative_ic_trend_accumulation_preregistration.py`.
- [ ] Mirror prior preregistration CLIs with `--output-dir`, `--min-candidates`, and `--allow-not-ready`.
- [ ] Print summary, negative IC context, and output directory.

## Task 4: Verify and Run Real Preregistration

- [ ] Run new tests and related preregistration tests:

```powershell
python -m unittest tests.unit.test_negative_ic_trend_accumulation_preregistration tests.unit.test_negative_ic_trend_accumulation_preregistration_cli tests.unit.test_capacity_safe_trend_accumulation_preregistration
```

- [ ] Run real CLI:

```powershell
python scripts\run_negative_ic_trend_accumulation_preregistration.py --output-dir data\reports\negative_ic_trend_accumulation_preregistration_round106_20260622 --min-candidates 8
```

## Task 5: Reports and Startup Gate

- [ ] Write Round106 research report.
- [ ] Write Round104-106 review covering:
  - Round104 preregistration.
  - Round105 positive-direction failure and negative-IC evidence.
  - Round106 anti-overheat preregistration.
  - Decision to run Round107 prescreen before any portfolio grid.
- [ ] Update startup gate:
  - `source_audit`: Round104-106 review.
  - `next_direction`: `round107_negative_ic_trend_accumulation_prescreen`.
  - add `round106_negative_ic_trend_accumulation_preregistration_read`.
  - add `round104_106_three_round_review_read`.
  - reject `negative_ic_trend_accumulation_portfolio_grid_before_prescreen`.

## Task 6: Final Verification

- [ ] Run:

```powershell
python -m unittest tests.unit.test_negative_ic_trend_accumulation_preregistration tests.unit.test_negative_ic_trend_accumulation_preregistration_cli tests.unit.test_capacity_safe_trend_accumulation_preregistration tests.unit.test_factor_mining_startup_gate_cli
```

- [ ] Run:

```powershell
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
```

- [ ] Run:

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --market CN --asset-type stock --confirm-start --output-dir data\reports\startup_gate_round106_20260622
```

- [ ] Run:

```powershell
python scripts\run_project_audit.py --json
```

- [ ] Run:

```powershell
python -m py_compile src\quant_robot\ops\negative_ic_trend_accumulation_preregistration.py scripts\run_negative_ic_trend_accumulation_preregistration.py
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
