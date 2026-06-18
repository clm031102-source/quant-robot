# Long-Cycle Factor Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a long-cycle replay and audit layer that freezes historical factor candidates, blocks false long-cycle claims when data coverage is short, and reports which historical candidates remain research leads.

**Architecture:** Add a focused `quant_robot.ops.long_cycle_replay` module plus a CLI wrapper. The module will parse candidate rows, inspect local bars, classify candidates with conservative audit gates, and write JSON/CSV/Markdown artifacts. Existing backtest and replay engines remain unchanged in this first slice.

**Tech Stack:** Python standard library, pandas, unittest, existing `scripts/bootstrap.py` import setup.

---

### Task 1: Candidate Registry And Coverage Core

**Files:**
- Create: `src/quant_robot/ops/long_cycle_replay.py`
- Test: `tests/unit/test_long_cycle_replay.py`

- [ ] **Step 1: Write failing tests**

```python
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.long_cycle_replay import (
    build_candidate_registry,
    build_long_cycle_coverage,
    build_long_cycle_replay_pack,
    write_long_cycle_replay_pack,
)


class LongCycleReplayTests(unittest.TestCase):
    def test_registry_deduplicates_candidates_and_preserves_parameters(self):
        rows = [
            {
                "case_id": "case_a",
                "market": "CN",
                "factor_name": "factor_x",
                "top_n": 50,
                "cost_bps": 10,
                "forward_horizon": 20,
                "source_report": "report_a",
            },
            {
                "case_id": "case_a",
                "market": "CN",
                "factor_name": "factor_x",
                "top_n": 50,
                "cost_bps": 20,
                "forward_horizon": 20,
                "source_report": "report_b",
            },
        ]

        registry = build_candidate_registry(rows)

        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[0]["case_id"], "case_a")
        self.assertEqual(registry[0]["market"], "CN")
        self.assertEqual(registry[0]["frozen_parameters"]["top_n"], 50)
        self.assertEqual(registry[0]["source_reports"], ["report_a", "report_b"])

    def test_coverage_blocks_when_available_history_starts_after_required_cycle(self):
        bars = pd.DataFrame(
            {
                "date": ["2023-07-03", "2024-01-02"],
                "asset_id": ["CN_A", "CN_B"],
                "market": ["CN", "CN"],
                "adj_close": [10.0, 11.0],
            }
        )

        coverage = build_long_cycle_coverage(bars, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertIn("history_starts_after_required_cycle_start", coverage["blockers"])
        self.assertEqual(coverage["date_start"], "2023-07-03")

    def test_replay_pack_marks_candidates_research_only_when_coverage_is_short(self):
        bars = pd.DataFrame(
            {
                "date": ["2023-07-03", "2024-01-02"],
                "asset_id": ["CN_A", "CN_B"],
                "market": ["CN", "CN"],
                "adj_close": [10.0, 11.0],
            }
        )
        candidates = [{"case_id": "case_a", "market": "CN", "factor_name": "factor_x", "sharpe": 4.2}]

        pack = build_long_cycle_replay_pack(candidates, bars, market="CN", required_start="2015-01-01")

        self.assertEqual(pack["stage"], "long_cycle_factor_replay")
        self.assertEqual(pack["coverage"]["status"], "insufficient")
        self.assertEqual(pack["summary"]["candidates"], 1)
        self.assertEqual(pack["candidate_decisions"][0]["decision_status"], "research_lead")
        self.assertIn("long_cycle_coverage_insufficient", pack["candidate_decisions"][0]["reasons"])
        self.assertIn("high_sharpe_overfit_warning", pack["candidate_decisions"][0]["reasons"])

    def test_writer_emits_json_markdown_and_csv_artifacts(self):
        pack = {
            "stage": "long_cycle_factor_replay",
            "summary": {"candidates": 1},
            "coverage": {"status": "insufficient"},
            "candidate_registry": [{"case_id": "case_a"}],
            "candidate_decisions": [{"case_id": "case_a", "decision_status": "research_lead"}],
            "markdown": "# Long-Cycle Factor Replay\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            write_long_cycle_replay_pack(tmp, pack)

            self.assertTrue((Path(tmp) / "long_cycle_replay_pack.json").exists())
            self.assertTrue((Path(tmp) / "long_cycle_replay_pack.md").exists())
            self.assertTrue((Path(tmp) / "candidate_registry.csv").exists())
            self.assertTrue((Path(tmp) / "candidate_decisions.csv").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.unit.test_long_cycle_replay`

Expected: fail because `quant_robot.ops.long_cycle_replay` does not exist.

- [ ] **Step 3: Implement minimal core**

Create functions:

```python
build_candidate_registry(rows: list[dict[str, object]]) -> list[dict[str, object]]
build_long_cycle_coverage(bars: pd.DataFrame, *, market: str, required_start: str) -> dict[str, object]
build_long_cycle_replay_pack(candidate_rows: list[dict[str, object]], bars: pd.DataFrame, *, market: str, required_start: str) -> dict[str, object]
write_long_cycle_replay_pack(output_dir: str | Path, pack: dict[str, object]) -> None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.unit.test_long_cycle_replay`

Expected: all tests pass.

### Task 2: CLI Wrapper

**Files:**
- Create: `scripts/run_long_cycle_factor_replay.py`
- Test: `tests/unit/test_long_cycle_factor_replay_cli.py`

- [ ] **Step 1: Write failing CLI test**

Create a test that writes a small candidates CSV and bars CSV into a temporary directory, runs `run_long_cycle_factor_replay`, and asserts that the output pack has `coverage.status == "insufficient"` and one candidate decision.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.unit.test_long_cycle_factor_replay_cli`

Expected: fail because the CLI module does not exist.

- [ ] **Step 3: Implement CLI**

The CLI reads:

- `--candidates-csv`
- `--bars-csv`
- `--market`
- `--required-start`
- `--output-dir`

It writes the same artifacts as the core writer and prints a small JSON summary.

- [ ] **Step 4: Run CLI tests**

Run: `.\.venv\Scripts\python.exe -m unittest tests.unit.test_long_cycle_factor_replay_cli`

Expected: all tests pass.

### Task 3: Real Candidate Audit Run

**Files:**
- Output only: `data/reports/long_cycle_factor_replay/*`

- [ ] **Step 1: Build an input candidate CSV from existing Batch 12 and CN ETF paper-ready rows**

Use existing report rows and handoff files. Keep data under `data/reports`.

- [ ] **Step 2: Run the long-cycle replay CLI**

Run the CLI against available local bars. If local bars start after `2015-01-01`, the output must be blocked as insufficient long-cycle coverage.

- [ ] **Step 3: Read and summarize the output**

Report candidate counts, coverage blockers, and which candidates remain research-only because the local history is too short.

### Self-Review

- Spec coverage: the plan covers frozen registry, coverage blocking, audit classification, reporting, CLI, and real artifact run.
- Placeholder scan: no implementation step uses placeholder text.
- Type consistency: the same function names are used in tests and implementation.
