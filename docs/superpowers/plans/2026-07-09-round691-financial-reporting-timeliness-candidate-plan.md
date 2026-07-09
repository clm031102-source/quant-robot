# Round691 Financial Reporting Timeliness Candidate Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and validate the Round691 CN stock `financial_reporting_timeliness` candidate plan gate input before any IC screening.

**Architecture:** This is a config-and-gate change. The candidate plan JSON declares five PIT-safe candidate hypotheses and all required CN stock controls; the gate script validates that research screening can begin while portfolio, promotion, and final-holdout work remain blocked.

**Tech Stack:** JSON candidate plan, PowerShell commands, existing Python gate scripts under `scripts/`, lightweight Markdown documentation.

---

## File Structure

- Create: `configs/factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json`
  - Responsibility: preregister the five active `financial_reporting_timeliness` candidates and declare all candidate plan gate controls.
- Create: `docs/research/cn_stock_round691_financial_reporting_timeliness_candidate_plan_gate_2026-07-09.md`
  - Responsibility: lightweight, Git-safe summary of the candidate plan gate result and next allowed action.
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`
  - Responsibility: add Round691 to the research index.
- Existing read-only gate outputs: `data/reports/round691_financial_reporting_timeliness_candidate_plan_gate_20260709/`
  - Responsibility: local generated evidence only. Do not stage or commit this directory.

### Task 1: Confirm Execution Context

**Files:**
- Read: `docs/superpowers/specs/2026-07-09-round691-financial-reporting-timeliness-design.md`
- Read: `docs/research/ROUND690_NEXT_STEPS_CHECKLIST.md`

- [ ] **Step 1: Confirm branch and clean baseline**

Run:

```powershell
git status --short --branch
git log --oneline -3 --decorate
```

Expected: current branch is `codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709`; no unstaged or staged changes before new edits.

- [ ] **Step 2: Confirm startup gates have current local evidence**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709 --current-branch codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709 --commits-allowed --pushes-allowed --confirm-start --output-dir data\reports\round691_factor_mining_startup_gate_20260709
```

Expected: Quant PM status is `ready`; factor mining startup status is `cleared`; blockers are `[]`.

### Task 2: Write Candidate Plan JSON

**Files:**
- Create: `configs/factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json`

- [ ] **Step 1: Add the JSON candidate plan**

Create a JSON object with these required top-level fields:

```json
{
  "stage": "round691_financial_reporting_timeliness_preregistration",
  "round": 691,
  "market": "CN",
  "asset_type": "stock",
  "source_audit": "docs/research/cn_stock_round690_financial_reporting_timeliness_backfill_progress_2026-07-08.md",
  "source_plan_doc": "docs/superpowers/specs/2026-07-09-round691-financial-reporting-timeliness-design.md",
  "scope": {
    "machine": "office_desktop",
    "task": "factor_batch",
    "branch": "codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709"
  }
}
```

Add `research_control_plan.declared_controls` with the exact nine default areas from `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`: `cn_stock_tradeability`, `financial_pit_timing`, `source_sample_integrity`, `industry_style_neutralization`, `etf_rotation_scope_boundary`, `portfolio_construction`, `strict_statistics`, `china_market_regime`, and `event_factors`.

Add `promotion_policy` with `promotion_allowed=false`, `portfolio_backtest_allowed_before_prescreen=false`, and every key in `REQUIRED_PROMOTION_POLICY_KEYS` set to `true`.

Add five `candidates` with `market=CN`, `asset_type=stock`, `registration_status=pre_registered`, `portfolio_backtest_allowed=false`, and `promotion_allowed=false`:

```json
[
  "frt_reporting_lag_short",
  "frt_reporting_lag_improvement_4q",
  "frt_reporting_lag_stability_8q",
  "frt_early_report_quality_combo",
  "frt_late_reporter_risk_avoidance"
]
```

- [ ] **Step 2: Validate JSON syntax before the gate**

Run:

```powershell
.\.venv\Scripts\python.exe -m json.tool configs\factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json > $null
```

Expected: exit code 0.

### Task 3: Run Candidate Plan Gate

**Files:**
- Read generated: `data/reports/round691_financial_reporting_timeliness_candidate_plan_gate_20260709/factor_mining_candidate_plan_gate.json`
- Read generated: `data/reports/round691_financial_reporting_timeliness_candidate_plan_gate_20260709/factor_mining_candidate_plan_gate.md`

- [ ] **Step 1: Run the gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json --output-dir data\reports\round691_financial_reporting_timeliness_candidate_plan_gate_20260709
```

Expected: status `research_ready`; `candidate_plan_gate_cleared=true`; `research_screen_allowed=true`; `portfolio_grid_allowed=false`; `promotion_allowed=false`; blockers `[]`.

- [ ] **Step 2: Validate expected active candidate names**

Run:

```powershell
@'
import json
from pathlib import Path
expected = {
    "frt_reporting_lag_short",
    "frt_reporting_lag_improvement_4q",
    "frt_reporting_lag_stability_8q",
    "frt_early_report_quality_combo",
    "frt_late_reporter_risk_avoidance",
}
packet = json.loads(Path("data/reports/round691_financial_reporting_timeliness_candidate_plan_gate_20260709/factor_mining_candidate_plan_gate.json").read_text(encoding="utf-8"))
active = {row["factor_name"] for row in packet["candidate_rows"] if row["active_for_gate"]}
assert packet["status"] == "research_ready", packet["status"]
assert packet["decision"]["candidate_plan_gate_cleared"] is True
assert packet["decision"]["portfolio_grid_allowed"] is False
assert packet["decision"]["promotion_allowed"] is False
assert packet["decision"]["blockers"] == []
assert active == expected, sorted(active)
print("round691_candidate_plan_gate_validated")
'@ | .\.venv\Scripts\python.exe -
```

Expected: prints `round691_candidate_plan_gate_validated`.

### Task 4: Write Lightweight Research Summary

**Files:**
- Create: `docs/research/cn_stock_round691_financial_reporting_timeliness_candidate_plan_gate_2026-07-09.md`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] **Step 1: Add the Round691 summary**

Create a Markdown summary that records:

- Branch and machine/task.
- Startup gate results.
- CN stock data manifest blockers and warnings.
- Candidate plan gate status and blockers.
- Five preregistered candidate names.
- Explicit blocks on IC screening before this gate, portfolio grids, promotion, sign/window tuning, mixed-window harvesting, and 2026 final-holdout reads.
- Next allowed action: start specialized PIT financial reporting timeliness prescreen using fixed 5D/20D horizons only.

- [ ] **Step 2: Update the research index**

Append a dated Round691 entry to `docs/research/CURRENT_RESEARCH_INDEX.md` linking to the summary and noting that generated `data/reports` evidence remains local and uncommitted.

### Task 5: Verify and Commit

**Files:**
- Stage only:
  - `configs/factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json`
  - `docs/superpowers/plans/2026-07-09-round691-financial-reporting-timeliness-candidate-plan.md`
  - `docs/research/cn_stock_round691_financial_reporting_timeliness_candidate_plan_gate_2026-07-09.md`
  - `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] **Step 1: Check forbidden paths are not staged**

Run:

```powershell
git status --short
git diff --check
git diff --cached --check
```

Expected: no `data/raw`, `data/processed`, `data/reports`, `.env`, log, Parquet, credential, broker, account, or order paths staged.

- [ ] **Step 2: Re-run the candidate gate as final verification**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json --output-dir data\reports\round691_financial_reporting_timeliness_candidate_plan_gate_20260709
```

Expected: status `research_ready`; blockers `[]`.

- [ ] **Step 3: Commit allowed source/docs/config changes**

Run:

```powershell
git add configs/factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json docs/superpowers/plans/2026-07-09-round691-financial-reporting-timeliness-candidate-plan.md docs/research/cn_stock_round691_financial_reporting_timeliness_candidate_plan_gate_2026-07-09.md docs/research/CURRENT_RESEARCH_INDEX.md
git commit -m "Register Round691 financial reporting timeliness candidates"
```

Expected: commit succeeds with only config and documentation changes.

## Self-Review

- Spec coverage: this plan implements the approved candidate-plan gate stage and explicitly excludes IC prescreening until the gate clears.
- Open-slot scan: no vague markers or open-ended implementation steps are permitted.
- Type consistency: candidate names, branch name, output directory, and config filename match the 2026-07-09 spec and gate command.
