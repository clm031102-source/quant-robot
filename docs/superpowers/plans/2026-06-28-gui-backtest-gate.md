# GUI Backtest Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Backtest Gate panel to the GUI control center that evaluates displayed research and paper metrics against minimum paper-handoff thresholds while keeping live trading blocked.

**Architecture:** Extend the existing pure `control_center` snapshot with a `backtest_gate` contract, render the contract in the static Dashboard using browser-side metrics, and verify through unit tests, browser smoke, and local browser checks.

**Tech Stack:** Python standard library, vanilla HTML/CSS/JavaScript, unittest, existing browser smoke script, existing project and sync audits.

---

### Task 1: Backend Backtest Gate Contract

**Files:**
- Modify: `tests/unit/test_gui.py`
- Modify: `src/quant_robot/gui/control_center.py`

- [ ] **Step 1: Write the failing snapshot test**

Add assertions inside `test_control_center_snapshot_exposes_work_backtest_method_and_safety`:

```python
self.assertIn("backtest_gate", result)
self.assertEqual(result["backtest_gate"]["stage"], "gui_backtest_gate")
self.assertFalse(result["backtest_gate"]["summary"]["live_trading_allowed"])
self.assertFalse(result["backtest_gate"]["summary"]["paper_candidate_allowed"])
gate_ids = {item["gate_id"] for item in result["backtest_gate"]["rows"]}
self.assertIn("sharpe", gate_ids)
self.assertIn("total_return", gate_ids)
self.assertIn("annualized_return", gate_ids)
self.assertIn("max_drawdown", gate_ids)
self.assertIn("win_rate", gate_ids)
self.assertIn("trade_count", gate_ids)
self.assertIn("benchmark_relative_return", gate_ids)
self.assertIn("paper_ending_equity", gate_ids)
self.assertIn("execution_receipts", gate_ids)
self.assertIn("live_boundary", gate_ids)
self.assertTrue(all(item.get("command") for item in result["backtest_gate"]["rows"]))
self.assertTrue(all(item.get("evidence") for item in result["backtest_gate"]["rows"]))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiSnapshotTests.test_control_center_snapshot_exposes_work_backtest_method_and_safety
```

Expected: fail with missing `backtest_gate`.

- [ ] **Step 3: Implement `_backtest_gate()`**

Build rows with thresholds for Sharpe, return, annualized return, drawdown, win rate, trade count, benchmark relative return, paper ending equity, execution receipts, and live boundary. Add the object to the returned control-center snapshot.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the same focused test. Expected: pass.

### Task 2: Frontend Panel

**Files:**
- Modify: `tests/unit/test_gui.py`
- Modify: `src/quant_robot/gui/static/index.html`
- Modify: `src/quant_robot/gui/static/app.js`
- Modify: `src/quant_robot/gui/static/styles.css`

- [ ] **Step 1: Write failing static assertions**

Add HTTP/static assertions:

```python
self.assertIn("control-backtest-gate", html)
self.assertIn("control-backtest-gate", app_js)
self.assertIn("renderBacktestGate", app_js)
self.assertIn("backtest_gate", control)
```

- [ ] **Step 2: Run HTTP test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiHttpTests.test_http_app_serves_index_snapshot_and_demo_workflows
```

Expected: fail because the panel and renderer are missing.

- [ ] **Step 3: Add Dashboard markup**

Add:

```html
<div class="control-cell">
  <small>Backtest gate</small>
  <div id="control-backtest-gate" class="control-list backtest-gate-list"></div>
</div>
```

- [ ] **Step 4: Add JavaScript renderer**

Read `const backtestGate = control.backtest_gate || {};` and render it with:

```javascript
byId("control-backtest-gate").innerHTML = renderBacktestGate(backtestGate, metrics, benchmark, paperMetrics);
```

Implement `renderBacktestGate()`, `gateMetricValue()`, `evaluateGateRow()`, and `formatGateValue()`.

- [ ] **Step 5: Add CSS sizing**

Add:

```css
.backtest-gate-list {
  max-height: 236px;
}
```

- [ ] **Step 6: Run HTTP test and verify GREEN**

Run the same HTTP test. Expected: pass.

### Task 3: Browser Smoke Contract

**Files:**
- Modify: `tests/unit/test_gui.py`
- Modify: `scripts/run_gui_browser_smoke.py`

- [ ] **Step 1: Write failing smoke expectation**

Add `backtest_gate_panel` to the browser-smoke test expected check IDs.

- [ ] **Step 2: Run smoke test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiSnapshotTests.test_gui_browser_smoke_script_writes_evidence_packet
```

Expected: fail until the smoke script includes the new check.

- [ ] **Step 3: Add smoke check**

Require HTML token `control-backtest-gate`, JS token `renderBacktestGate`, API `backtest_gate.stage == gui_backtest_gate`, API summary `live_trading_allowed is False`, and CSS token `.backtest-gate-list`.

- [ ] **Step 4: Run smoke test and verify GREEN**

Run the same smoke test. Expected: pass.

### Task 4: Verification And Publish

**Files:**
- No extra production files unless verification reveals a defect.

- [ ] **Step 1: Run GUI unit suite**

```powershell
python -m unittest -v tests.unit.test_gui
```

- [ ] **Step 2: Run compile checks**

```powershell
python -m compileall -q src\quant_robot\gui scripts\run_gui_control_center_audit.py scripts\run_gui_browser_smoke.py
```

- [ ] **Step 3: Run project audit**

```powershell
python scripts\run_project_audit.py --json
```

- [ ] **Step 4: Restart local GUI and run browser smoke**

```powershell
python scripts\run_gui_browser_smoke.py --base-url http://127.0.0.1:8765 --output-dir data\reports\gui_browser_smoke
```

- [ ] **Step 5: Run independent GUI audit**

```powershell
python scripts\run_gui_control_center_audit.py --output-dir data\reports\gui_control_center_audit
```

- [ ] **Step 6: Sync audit, commit, and push**

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_review
git diff --check
git add docs/superpowers/specs/2026-06-28-gui-backtest-gate-design.md docs/superpowers/plans/2026-06-28-gui-backtest-gate.md src/quant_robot/gui/control_center.py src/quant_robot/gui/static/index.html src/quant_robot/gui/static/app.js src/quant_robot/gui/static/styles.css scripts/run_gui_browser_smoke.py tests/unit/test_gui.py
git commit -m "feat: add gui backtest gate"
git push origin codex/gui-control-center-mvp-20260627
```

### Task 5: Audit Repair Patch

Independent GUI auditors found that the first implementation could mislead the operator in three ways:

- Drawdown used the wrong sign convention. Project `max_drawdown` values are negative, so the gate must use `max_drawdown >= -0.30`, not `<= 0.30`.
- Browser receipts must be tied to the currently displayed research and paper requests. Counting all localStorage receipts is not sufficient.
- The frontend must not label a result as a paper candidate when the backend summary still has `paper_candidate_allowed == false`.

Repair acceptance:

- Unit tests assert the negative drawdown threshold and request-bound receipt metadata.
- Static frontend assertions require request matching, current safety lookup, paper initial-cash thresholding, and gate rerender after receipt append.
- Node VM validation confirms stale receipts do not pass the gate, fresh matching research/paper receipts do pass the receipt row, severe negative drawdown fails, and live-trading regressions fail; browser DOM validation confirms the corrected gate renders without overflow.
