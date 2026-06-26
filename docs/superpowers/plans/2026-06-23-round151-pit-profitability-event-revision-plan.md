# Round151 PIT Profitability Event Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preregistration-only Round151 entrypoint for PIT-aware profitability event revision candidates, replacing failed lottery/MAX-effect continuation with a new financial-information-timing family.

**Architecture:** Add a focused preregistration module plus CLI and tests. The module reuses the existing `fina_indicator` loader, declares 10 event/revision candidates, gates candidate coverage and endpoint availability, and emits JSON/Markdown/CSV artifacts.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops` preregistration patterns, existing candidate-plan gate.

---

### Task 1: Unit Tests For Round151 Preregistration

**Files:**
- Create: `tests/unit/test_profitability_event_revision_preregistration.py`

- [ ] **Step 1: Write failing tests**

Create tests that import the not-yet-existing module:

```python
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.factor_mining_candidate_plan_gate import build_factor_mining_candidate_plan_gate
from quant_robot.ops.profitability_event_revision_preregistration import (
    build_profitability_event_revision_preregistration,
    default_profitability_event_revision_candidate_specs,
    write_profitability_event_revision_preregistration,
)
from quant_robot.storage.dataset_store import DatasetStore


class ProfitabilityEventRevisionPreregistrationTests(unittest.TestCase):
    def test_preregisters_pit_revision_candidates_without_portfolio_permission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _financial_rows())

            result = build_profitability_event_revision_preregistration(
                input_root=root,
                endpoint_probe_results={
                    "forecast": {"ok": True, "rows": 120, "columns": ["ann_date", "end_date", "p_change_min", "p_change_max"]},
                    "express": {"ok": True, "rows": 120, "columns": ["ann_date", "end_date", "yoy_net_profit", "diluted_roe"]},
                },
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )

        self.assertEqual(result["stage"], "profitability_event_revision_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertGreaterEqual(result["summary"]["coverage_passed_candidates"], 6)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("pit_fina_netprofit_yoy_revision_1q", names)
        self.assertIn("pit_forecast_profit_revision_event_1q", names)
        self.assertNotIn("fina_roe_level", names)
        plan_gate = build_factor_mining_candidate_plan_gate(result, gate_stage="discovery")
        self.assertTrue(plan_gate["decision"]["candidate_plan_gate_cleared"])
        self.assertFalse(plan_gate["decision"]["portfolio_grid_allowed"])

    def test_blocks_endpoint_candidates_without_endpoint_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _financial_rows())

            result = build_profitability_event_revision_preregistration(
                input_root=root,
                endpoint_probe_results={},
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )

        candidates = {candidate["factor_name"]: candidate for candidate in result["candidates"]}
        self.assertEqual(candidates["pit_forecast_profit_revision_event_1q"]["registration_status"], "blocked_by_endpoint_availability")
        self.assertEqual(candidates["pit_express_profit_surprise_event_1q"]["registration_status"], "blocked_by_endpoint_availability")
        self.assertTrue(result["summary"]["passes"])

    def test_blocks_duplicate_or_round96_static_candidate_names(self) -> None:
        specs = list(default_profitability_event_revision_candidate_specs())
        specs = [specs[0], specs[0]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _financial_rows())
            result = build_profitability_event_revision_preregistration(
                input_root=root,
                candidate_specs=specs,
                min_assets=3,
                min_passed_candidates=1,
            )
        self.assertFalse(result["summary"]["passes"])
        self.assertIn("duplicate_candidate_names", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "output"
            _write_fina_indicator_inputs(root, _financial_rows())
            result = build_profitability_event_revision_preregistration(
                input_root=root,
                min_assets=3,
                min_passed_candidates=6,
            )
            write_profitability_event_revision_preregistration(output, result)
            self.assertTrue((output / "profitability_event_revision_preregistration.json").exists())
            self.assertTrue((output / "profitability_event_revision_preregistration.md").exists())
            self.assertTrue((output / "profitability_event_revision_candidates.csv").exists())


def _financial_rows() -> pd.DataFrame:
    rows = []
    periods = pd.period_range("2022Q1", "2024Q4", freq="Q")
    for asset_idx in range(3):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        for period_idx, period in enumerate(periods):
            end_date = period.end_time.normalize()
            ann_date = end_date + pd.Timedelta(days=30 + asset_idx)
            rows.append({
                "date": ann_date,
                "asset_id": asset_id,
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "source": "tushare_fina_indicator",
                "ann_date": ann_date,
                "end_date": end_date,
                "roe": 8.0 + asset_idx + period_idx * 0.2,
                "roa": 3.0 + asset_idx + period_idx * 0.1,
                "grossprofit_margin": 20.0 + period_idx,
                "netprofit_margin": 6.0 + period_idx * 0.5,
                "netprofit_yoy": 5.0 + period_idx * 1.2,
                "or_yoy": 4.0 + period_idx * 0.8,
                "ocfps": 1.0 + period_idx * 0.1,
                "cfps": 1.2 + period_idx * 0.1,
            })
    return pd.DataFrame(rows)


def _write_fina_indicator_inputs(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/fina_indicator_inputs",
        {"frequency": "1q", "market": "CN", "year": "2024"},
    )
```

- [ ] **Step 2: Run tests to verify RED**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_preregistration`

Expected: import failure for `quant_robot.ops.profitability_event_revision_preregistration`.

### Task 2: Implement Preregistration Module

**Files:**
- Create: `src/quant_robot/ops/profitability_event_revision_preregistration.py`

- [ ] **Step 1: Add dataclass and default candidate specs**

Implement `ProfitabilityEventRevisionCandidateSpec` with fields for candidate metadata, required financial columns, optional endpoints, event date fields, PIT controls, and permissions fixed false by default.

- [ ] **Step 2: Add builder and gates**

Implement `build_profitability_event_revision_preregistration(...)` to:

- load `fina_indicator` rows via `_load_fina_indicator_inputs`;
- reuse dataset quality checks compatible with Round96;
- compute candidate coverage from required financial columns and minimum history;
- block endpoint-dependent candidates when endpoint proof is missing;
- block duplicate names and rejected Round96 static names;
- include `research_control_plan=default_cn_stock_pre_mining_control_plan()`;
- set `next_required_gate=round152_pit_profitability_event_revision_matrix_and_label_smoke`;
- keep portfolio and promotion false.

- [ ] **Step 3: Add writer and Markdown renderer**

Write:

- `profitability_event_revision_preregistration.json`
- `profitability_event_revision_preregistration.md`
- `profitability_event_revision_candidates.csv`

- [ ] **Step 4: Run tests to verify GREEN**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_preregistration`

Expected: all tests pass.

### Task 3: CLI Test And CLI

**Files:**
- Create: `tests/unit/test_profitability_event_revision_preregistration_cli.py`
- Create: `scripts/run_profitability_event_revision_preregistration.py`

- [ ] **Step 1: Write CLI failing test**

The test should create temp `fina_indicator` rows, call `run_profitability_event_revision_preregistration_cli(...)`, and assert JSON/MD/CSV outputs exist.

- [ ] **Step 2: Run CLI test to verify RED**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_preregistration_cli`

Expected: import failure for missing script.

- [ ] **Step 3: Implement CLI**

Expose:

- `--input-root`
- `--output-dir`
- `--min-assets`
- `--min-passed-candidates`
- `--allow-not-ready`

The CLI should not fetch live endpoints by default. It should pass an empty endpoint probe unless explicit endpoint JSON support is later added.

- [ ] **Step 4: Run CLI tests to verify GREEN**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_preregistration_cli`

Expected: all tests pass.

### Task 4: Run Round151 On Existing PIT Financial Shard

**Files:**
- Output only under `data/reports/profitability_event_revision_preregistration_round151_20260623`

- [ ] **Step 1: Run Round151 CLI**

Run:

`python scripts\run_profitability_event_revision_preregistration.py --input-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --output-dir data\reports\profitability_event_revision_preregistration_round151_20260623 --min-assets 80 --min-passed-candidates 6`

Expected: preregistration completes; endpoint-dependent candidates may be blocked, but financial revision candidates should pass if coverage is sufficient.

- [ ] **Step 2: Run candidate plan gate**

Run:

`python scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan data\reports\profitability_event_revision_preregistration_round151_20260623\profitability_event_revision_preregistration.json --gate-stage discovery --output-dir data\reports\factor_mining_candidate_plan_gate_round151_20260623`

Expected: `candidate_plan_gate_cleared=true`, `portfolio_grid_allowed=false`.

### Task 5: Docs, Startup Direction, And Three-Round Review

**Files:**
- Create: `docs/research/cn_stock_profitability_event_revision_preregistration_round151_2026-06-23.md`
- Create: `docs/research/cn_stock_round149_151_three_round_review_2026-06-23.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py` if startup direction assertions change.

- [ ] **Step 1: Write Round151 report**

Summarize candidates, coverage, endpoint blocks, and next required gate.

- [ ] **Step 2: Write Round149-151 review**

Review:

- Round149 preregistered 6 lottery candidates;
- Round150 rejected lottery as standalone long alpha after 0 research leads;
- Round151 rotated to PIT profitability event revision preregistration.

- [ ] **Step 3: Update startup config**

Set:

`source_audit=docs/research/cn_stock_round149_151_three_round_review_2026-06-23.md`

Set next direction:

`round152_pit_profitability_event_revision_matrix_and_label_smoke`

- [ ] **Step 4: Run verification**

Run:

`python -m unittest tests.unit.test_profitability_event_revision_preregistration tests.unit.test_profitability_event_revision_preregistration_cli tests.unit.test_factor_mining_candidate_plan_gate tests.unit.test_factor_mining_startup_gate tests.unit.test_factor_mining_startup_gate_cli`

Run:

`python -m py_compile src\quant_robot\ops\profitability_event_revision_preregistration.py scripts\run_profitability_event_revision_preregistration.py`

Run:

`git ls-files data/raw data/processed data/reports`

Expected: tests pass, compile exits 0, data outputs are not Git-tracked.
