# Round91 Fina Indicator Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a planning-only, resume-safe long-history Tushare `fina_indicator` backfill plan before profitability factor mining resumes.

**Architecture:** Keep the planner pure and deterministic under `quant_robot.ops`, with a thin CLI wrapper for artifact writing. The planner never calls Tushare; the existing ingestion module remains the only component that downloads data.

**Tech Stack:** Python standard library, `pandas` for date handling, `unittest`, existing repository CLI bootstrap.

---

### Task 1: Planner Unit Tests

**Files:**
- Create: `tests/unit/test_fina_indicator_backfill_plan.py`
- Create later: `src/quant_robot/ops/fina_indicator_backfill_plan.py`

- [ ] **Step 1: Write failing tests**

```python
import unittest

from quant_robot.ops.fina_indicator_backfill_plan import build_fina_indicator_backfill_plan


class FinaIndicatorBackfillPlanTests(unittest.TestCase):
    def test_builds_quarterly_request_plan(self) -> None:
        plan = build_fina_indicator_backfill_plan(
            symbols=["000001.SZ", "600519.SH"],
            start_period="2015-03-31",
            end_period="2025-12-31",
            batch_size=20,
            max_requests=200,
        )

        self.assertEqual(plan["summary"]["period_count"], 44)
        self.assertEqual(plan["summary"]["symbol_count"], 2)
        self.assertEqual(plan["summary"]["request_count"], 88)
        self.assertEqual(plan["summary"]["batch_count"], 5)
        self.assertTrue(plan["summary"]["passes"])
        self.assertEqual(plan["periods"][0], "20150331")
        self.assertEqual(plan["periods"][-1], "20251231")
        self.assertEqual(plan["request_batches"][0]["requests"][0], {"ts_code": "000001.SZ", "period": "20150331"})

    def test_blocks_when_request_budget_is_exceeded(self) -> None:
        plan = build_fina_indicator_backfill_plan(
            symbols=["000001.SZ", "600519.SH"],
            start_period="2015-03-31",
            end_period="2025-12-31",
            batch_size=20,
            max_requests=20,
        )

        self.assertFalse(plan["summary"]["passes"])
        self.assertIn("request_count_exceeds_max_requests", plan["summary"]["blockers"])
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m unittest tests.unit.test_fina_indicator_backfill_plan
```

Expected: fail with missing `quant_robot.ops.fina_indicator_backfill_plan`.

- [ ] **Step 3: Implement planner**

Create `src/quant_robot/ops/fina_indicator_backfill_plan.py` with:

```python
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd

STAGE = "tushare_fina_indicator_backfill_plan"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_fina_indicator_backfill_plan(
    *,
    symbols: list[str],
    start_period: str,
    end_period: str,
    batch_size: int = 500,
    max_requests: int | None = None,
) -> dict[str, Any]:
    ...
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m unittest tests.unit.test_fina_indicator_backfill_plan
```

Expected: all tests pass.

### Task 2: CLI Tests And Wrapper

**Files:**
- Create: `tests/unit/test_fina_indicator_backfill_plan_cli.py`
- Create: `scripts/run_fina_indicator_backfill_plan.py`

- [ ] **Step 1: Write failing CLI test**

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_fina_indicator_backfill_plan import run_fina_indicator_backfill_plan_cli


class FinaIndicatorBackfillPlanCliTests(unittest.TestCase):
    def test_cli_writes_plan_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "report"

            result = run_fina_indicator_backfill_plan_cli(
                symbols=["000001.SZ", "600519.SH"],
                start_period="2015-03-31",
                end_period="2025-12-31",
                batch_size=20,
                max_requests=200,
                output_dir=output_dir,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "fina_indicator_backfill_plan.json").exists())
            self.assertTrue((output_dir / "fina_indicator_backfill_plan.md").exists())
            payload = json.loads((output_dir / "fina_indicator_backfill_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["request_count"], 88)
```

- [ ] **Step 2: Run CLI test to verify RED**

Run:

```powershell
python -m unittest tests.unit.test_fina_indicator_backfill_plan_cli
```

Expected: fail with missing script.

- [ ] **Step 3: Implement CLI wrapper**

Create `scripts/run_fina_indicator_backfill_plan.py` with `run_fina_indicator_backfill_plan_cli(...)`, `--symbols`, `--symbols-file`, period, batch, budget, and output arguments.

- [ ] **Step 4: Run CLI test to verify GREEN**

Run:

```powershell
python -m unittest tests.unit.test_fina_indicator_backfill_plan_cli
```

Expected: all tests pass.

### Task 3: Round91 Artifacts And Startup Gate

**Files:**
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Create: `docs/research/cn_stock_tushare_fina_indicator_backfill_plan_round91_2026-06-21.md`

- [ ] **Step 1: Generate a smoke plan artifact**

Run:

```powershell
python scripts\run_fina_indicator_backfill_plan.py --symbols 000001.SZ,600519.SH --start-period 2015-03-31 --end-period 2025-12-31 --batch-size 20 --max-requests 200 --output-dir data\reports\fina_indicator_backfill_plan_round91_20260621
```

Expected: JSON summary with `period_count=44`, `symbol_count=2`, `request_count=88`, `passes=true`.

- [ ] **Step 2: Update startup gate**

Set `repeatable_mining_protocol.source_audit` to the Round91 research report and `next_direction` to `round92_tushare_fina_indicator_limited_symbol_backfill_smoke`.

- [ ] **Step 3: Write research report**

Document that Round91 produced no factor and no profitability claim. The accepted outcome is a reusable long-history backfill plan for later PIT financial factors.

### Task 4: Verification

**Files:**
- No additional files.

- [ ] **Step 1: Run focused tests**

```powershell
python -m unittest tests.unit.test_fina_indicator_backfill_plan tests.unit.test_fina_indicator_backfill_plan_cli tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_project_audit
```

- [ ] **Step 2: Run startup gate**

```powershell
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start
```

- [ ] **Step 3: Run project audit and whitespace check**

```powershell
python scripts\run_project_audit.py --json
git diff --check
```
