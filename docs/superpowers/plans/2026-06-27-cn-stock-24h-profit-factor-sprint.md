# CN Stock 24h Profit Factor Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the strongest CN stock research-to-paper factor candidate set for simulation preparation within the 24h sprint, with evidence from long-sample full-period metrics, OOS windows, transaction-cost stress, beta/residual checks, tradeability/execution checks, and three-round audit reviews.

**Architecture:** Keep 2026 final holdout sealed. Use the current office desktop branch for CN stock factor validation, promote only candidates that survive reusable gates, and record rejected families so the search changes direction instead of repeating weak variants.

**Tech Stack:** Python, pandas, project `scripts/` entrypoints, `src/quant_robot/ops/` reusable modules, JSON config, Markdown research reports, unittest.

---

### Task 1: Startup And Scope Lock

**Files:**
- Read: `configs/workstations.json`
- Read: `configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`
- Modify: `docs/research/cn_stock_profit_sprint_simulation_shortlist_runbook_2026-06-27.md`

- [ ] **Step 1: Confirm machine and task context**

Run:

```powershell
python scripts\start_task_context.py
git status --short --branch
```

Expected: branch is `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`; task is `factor_validation`; no generated data paths are staged for Git.

- [ ] **Step 2: Write the current sprint objective into the runbook**

Record that this office desktop sprint is CN stock factor validation only, with no broker/account/order/live-trading access and 2026 final holdout sealed.

- [ ] **Step 3: Verify config still parses**

Run:

```powershell
python -m json.tool configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json > $null
```

Expected: exit code 0.

### Task 2: Repair Execution-Causality Candidate

**Files:**
- Create or modify: `src/quant_robot/ops/shortlist_delayed_exit_return_repair.py`
- Create or modify: `scripts/run_shortlist_delayed_exit_return_repair.py`
- Test: `tests/unit/test_shortlist_delayed_exit_return_repair.py`
- Test: `tests/unit/test_shortlist_delayed_exit_return_repair_cli.py`

- [ ] **Step 1: Write the failing zero-event preservation test**

Add a test asserting that entry-blocked or unresolved delayed-exit trades keep the planned `exit_date` and zero return, so downstream event grouping cannot silently drop them.

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m unittest tests.unit.test_shortlist_delayed_exit_return_repair
```

Expected: failure proves the zero-return row date is missing before the fix.

- [ ] **Step 3: Implement delayed-exit return repair**

Implement a reusable function that finds the first sellable exit date within the configured window, recomputes return from entry price to delayed exit price, and writes planned exit date for zero-return unresolved rows.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m unittest tests.unit.test_shortlist_delayed_exit_return_repair tests.unit.test_shortlist_delayed_exit_return_repair_cli
```

Expected: all tests pass.

### Task 3: Candidate Handoff Gate

**Files:**
- Modify: `configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`
- Modify: `docs/research/cn_stock_profit_sprint_simulation_shortlist_runbook_2026-06-27.md`
- Create: `docs/research/cn_stock_round430_432_three_round_audit_2026-06-27.md`

- [ ] **Step 1: Record Round431 rejected public-tilt risk caps**

Add metrics showing caps reduce drawdown/extreme contribution only marginally and trail the uncapped candidate on return, OOS overlap, and beta-hedged annualized return.

- [ ] **Step 2: Record Round432 delayed-exit candidate**

Add metrics for `round432_delayed_exit_m150`: annualized 6.663%, total return +218.46%, Sharpe 0.968, overlap Sharpe 0.496, max drawdown -26.21%, mean OOS annualized 10.043%, strict OOS pass 90%, beta-hedged annualized 7.485%, alpha t 4.36.

- [ ] **Step 3: Create the three-round audit**

State that Round430 found a useful but not clean `roundtrip` proxy, Round431 rejected risk-cap threshold tuning, and Round432 became the best research-to-paper candidate pending heavy-cost and replay/handoff gates.

- [ ] **Step 4: Verify config and shortlist checks**

Run:

```powershell
python -m json.tool configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json > $null
python scripts\check_simulation_shortlist_config.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json
```

Expected: both commands exit 0.

### Task 4: Heavy-Cost Stress For Best Candidate

**Files:**
- Modify if needed: `src/quant_robot/ops/shortlist_delayed_exit_return_repair.py`
- Modify if needed: `scripts/run_shortlist_delayed_exit_return_repair.py`
- Test if code changes: `tests/unit/test_shortlist_delayed_exit_return_repair.py`
- Output only, not committed: `data/reports/round433_24h_profit_sprint_delayed_exit_cost_stress_20260627`

- [ ] **Step 1: Write a failing test before any cost override code change**

If the delayed-exit repair needs a cost override, add a test that verifies `--override-cost-rate` recomputes the weighted return with the requested bps.

- [ ] **Step 2: Run 10/20/30 bps delayed-exit variants**

Use the same trade source, bar folders, tradeability masks, and cohort entry-timed builder as Round432.

- [ ] **Step 3: Compare against Round425 and Round424 cost lanes**

Keep the candidate only if it remains economically useful after 20/30bps and does not breach the user's roughly -30% drawdown tolerance without compensating return.

### Task 5: Continue Mining With Direction Rotation

**Files:**
- Modify: future `docs/research/cn_stock_round*_*.md`
- Modify: future `configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`

- [ ] **Step 1: Every three rounds, create an audit**

Audit must list promoted candidates, rejected families, hidden risk found, and the next family to test.

- [ ] **Step 2: Rotate families when a line fails**

Do not keep extending one weak family. Rotate among execution/tradeability, public technical indicators, event context, PIT accounting quality, market regime, industry/size/value/liquidity neutralization, and capacity/cost controls.

- [ ] **Step 3: Every ten rounds, run safe sync before pushing**

Run:

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_validation
```

Only run `--execute --push` if the audit says changed paths are syncable, validation passed, branch discovery has no errors, and no forbidden data/token/broker/account/order paths are present.
