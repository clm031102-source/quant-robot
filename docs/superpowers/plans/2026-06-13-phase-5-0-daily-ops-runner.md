# Phase 5.0 Daily Ops Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily research-to-paper-trading operations runner that turns current CN ETF evidence into a decision pack, advisory rebalance tickets, simulation metrics, and safety gates without broker connectivity.

**Architecture:** Add a focused `quant_robot.ops.daily_ops` module that orchestrates existing promotion/readiness, signal snapshot, rebalance, and paper simulation code. Add a small CLI wrapper in `scripts/run_daily_ops.py`. Keep all broker/account/order placement boundaries disabled and write local JSON/Markdown/CSV artifacts under `data/reports/daily_ops`.

**Tech Stack:** Python 3, pandas, existing `quant_robot` modules, `unittest`, local JSON/CSV/Markdown artifacts.

---

### Task 1: Daily Ops Decision Pack Core

**Files:**
- Create: `src/quant_robot/ops/daily_ops.py`
- Test: `tests/unit/test_daily_ops.py`

- [ ] **Step 1: Write the failing test**

```python
def test_daily_ops_pack_builds_paper_ready_decision_from_current_artifacts(self):
    promotion = {
        "selected_candidate": {
            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
            "market": "CN_ETF",
            "factor_name": "liquidity_10",
            "rank": 1,
        },
    }
    readiness = {
        "overall_status": "blocked",
        "readiness_items": [
            {"track_id": "data_quality", "status": "pass", "evidence": "gap_resolution=non_blocking"},
            {"track_id": "provider_readiness", "status": "pass", "evidence": "ready_market_providers=2/2"},
            {"track_id": "manual_review_gate", "status": "block", "evidence": "manual_live_review_not_enabled"},
            {"track_id": "research_boundary", "status": "pass", "evidence": "order_placement=disabled"},
        ],
        "blocker_register": [{"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}],
    }
    signal = {"as_of_date": "2026-06-12", "targets": [{"asset_id": "CN_ETF_XSHG_510300", "target_weight": 1.0}], "rebalance_plan": []}
    simulation = {"metrics": {"total_return": 0.12, "max_equity_drawdown": -0.08}, "fills": [], "guard_events": []}

    pack = build_daily_ops_pack(promotion, readiness, signal, simulation)

    self.assertEqual(pack["stage"], "phase_5_0_daily_ops")
    self.assertEqual(pack["decision"]["status"], "paper_ready")
    self.assertFalse(pack["decision"]["live_boundary_allowed"])
    self.assertEqual(pack["decision"]["blocking_reasons"], ["manual_live_review_not_enabled"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest tests.unit.test_daily_ops`

Expected: import error or missing `build_daily_ops_pack`.

- [ ] **Step 3: Write minimal implementation**

Create `build_daily_ops_pack()`, `write_daily_ops_pack()`, and Markdown rendering. The decision is `paper_ready` when all non-manual readiness tracks pass/warn and only manual-live-review blockers remain; it is `blocked` when data/provider/research-boundary blockers remain. The live boundary is always disabled.

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest tests.unit.test_daily_ops`

Expected: OK.

### Task 2: Daily Ops CLI

**Files:**
- Create: `scripts/run_daily_ops.py`
- Test: `tests/unit/test_daily_ops_cli.py`

- [ ] **Step 1: Write failing CLI test**

Create temp promotion/readiness/signal/simulation JSON files, run `run_daily_ops(...)`, and assert it writes `daily_ops_pack.json`, `daily_ops_pack.md`, `daily_ops_tickets.csv`, and `daily_ops_summary.csv`.

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest tests.unit.test_daily_ops_cli`

Expected: import error for `scripts.run_daily_ops`.

- [ ] **Step 3: Implement CLI**

Read existing artifact paths by default:
- `data/reports/promotion_review/promotion_review_packet.json`
- `data/reports/pre_api_readiness_board/pre_api_readiness_board.json`
- `data/reports/signal_snapshot/daily_signal_snapshot.json` if present, otherwise build a signal snapshot from processed bars
- `data/reports/paper_simulation/manifest.json` if present, otherwise build a paper simulation summary from processed bars

Write the pack to `data/reports/daily_ops`.

- [ ] **Step 4: Run CLI test**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest tests.unit.test_daily_ops_cli`

Expected: OK.

### Task 3: Project Verification

**Files:**
- Modify only if needed: `scripts/run_checks.py`
- Create if needed: `docs/phase_5_0_daily_ops_runner.md`

- [ ] **Step 1: Run focused tests**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest tests.unit.test_daily_ops tests.unit.test_daily_ops_cli`

Expected: OK.

- [ ] **Step 2: Run full tests**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest discover -s tests`

Expected: OK.

- [ ] **Step 3: Run compile check**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m compileall -q src scripts tests`

Expected: exit code 0.

- [ ] **Step 4: Generate the real project daily pack**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe scripts\run_daily_ops.py --output-dir data\reports\daily_ops`

Expected: JSON summary with `stage=phase_5_0_daily_ops`, `live_boundary_allowed=false`, and local artifacts written.
