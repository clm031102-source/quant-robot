# GUI Workflow Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a workflow trace to the GUI control center so operators can see the active workflow, queued workflow, verification/audit gates, publish step, evidence storage, and live-blocked boundary in one chain.

**Architecture:** Extend the existing pure `control_center` snapshot, render it in the current static dashboard, and verify it through unit tests plus the local browser smoke packet. No new dependencies or broker-side behavior are introduced.

**Tech Stack:** Python standard library, vanilla HTML/CSS/JavaScript, unittest, existing browser smoke script, existing project sync audit.

---

### Task 1: Backend Workflow Trace Contract

**Files:**
- Modify: `tests/unit/test_gui.py`
- Modify: `src/quant_robot/gui/control_center.py`

- [ ] **Step 1: Write the failing snapshot test**

Add assertions inside `test_control_center_snapshot_exposes_work_backtest_method_and_safety`:

```python
self.assertIn("workflow_trace", result)
self.assertEqual(result["workflow_trace"]["stage"], "gui_workflow_trace")
self.assertEqual(result["workflow_trace"]["summary"]["current_workflow"], "research_backtest")
self.assertTrue(result["workflow_trace"]["summary"]["paper_only"])
self.assertFalse(result["workflow_trace"]["summary"]["live_trading_allowed"])
trace_ids = {item["trace_id"] for item in result["workflow_trace"]["rows"]}
self.assertIn("startup_health", trace_ids)
self.assertIn("research_backtest", trace_ids)
self.assertIn("result_evidence", trace_ids)
self.assertIn("signal_snapshot", trace_ids)
self.assertIn("paper_simulation", trace_ids)
self.assertIn("verification_pack", trace_ids)
self.assertIn("audit_packet", trace_ids)
self.assertIn("publish_branch", trace_ids)
self.assertIn("live_boundary", trace_ids)
self.assertTrue(all(item.get("command") for item in result["workflow_trace"]["rows"]))
self.assertTrue(all(item.get("evidence") for item in result["workflow_trace"]["rows"]))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiSnapshotTests.test_control_center_snapshot_exposes_work_backtest_method_and_safety
```

Expected: fail with missing `workflow_trace`.

- [ ] **Step 3: Implement the snapshot**

In `build_control_center_snapshot()`, compute `run_queue = _run_queue(workflows)`, then compute:

```python
workflow_trace = _workflow_trace(
    workflows,
    run_queue,
    startup_health,
    result_evidence,
    release_readiness,
    execution_receipts,
)
```

Add `"workflow_trace": workflow_trace` and reuse `run_queue` in the returned dictionary. Implement `_workflow_trace()` with nine rows: startup health, research backtest, result evidence, signal snapshot, paper simulation, verification pack, audit packet, publish branch, and live boundary.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the same focused unit test. Expected: pass.

### Task 2: Frontend Workflow Trace Panel

**Files:**
- Modify: `tests/unit/test_gui.py`
- Modify: `src/quant_robot/gui/static/index.html`
- Modify: `src/quant_robot/gui/static/app.js`
- Modify: `src/quant_robot/gui/static/styles.css`

- [ ] **Step 1: Write failing HTTP/static assertions**

Add assertions in the HTTP GUI test:

```python
self.assertIn("control-workflow-trace", html)
self.assertIn("renderWorkflowTrace", app_js)
self.assertIn("workflow_trace", control)
```

Add an app-js renderer assertion near the other control center renderer checks:

```python
self.assertIn("renderWorkflowTrace", app_js)
```

- [ ] **Step 2: Run the HTTP test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiHttpTests.test_http_app_serves_index_snapshot_and_demo_workflows
```

Expected: fail because the HTML id and renderer are missing.

- [ ] **Step 3: Add the HTML panel**

Insert a `Workflow trace` control cell near `Execution plan`:

```html
<div class="control-cell">
  <small>Workflow trace</small>
  <div id="control-workflow-trace" class="control-list workflow-trace-list"></div>
</div>
```

- [ ] **Step 4: Add JavaScript rendering**

In `renderControlCenter()`, read:

```javascript
const workflowTrace = control.workflow_trace || {};
```

Then render:

```javascript
byId("control-workflow-trace").innerHTML = renderWorkflowTrace(workflowTrace);
```

Implement `renderWorkflowTrace()` with a summary row and up to nine trace rows, escaping status, command, endpoint, evidence, and next action.

- [ ] **Step 5: Add CSS sizing**

Add:

```css
.workflow-trace-list {
  max-height: 236px;
}
```

- [ ] **Step 6: Run the HTTP test and verify GREEN**

Run the same HTTP test. Expected: pass.

### Task 3: Browser Smoke Contract

**Files:**
- Modify: `tests/unit/test_gui.py`
- Modify: `scripts/run_gui_browser_smoke.py`

- [ ] **Step 1: Write failing browser-smoke assertions**

Update expected smoke check IDs in `tests/unit/test_gui.py` to include `workflow_trace_panel`.

- [ ] **Step 2: Run the smoke unit test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiSnapshotTests.test_gui_browser_smoke_script_writes_packet
```

Expected: fail until the smoke script includes the new check.

- [ ] **Step 3: Add the smoke check**

In `scripts/run_gui_browser_smoke.py`, require:

- HTML token `control-workflow-trace`.
- App JS token `renderWorkflowTrace`.
- API `workflow_trace.stage == gui_workflow_trace`.
- API `workflow_trace.summary.paper_only is True`.
- CSS token `.workflow-trace-list`.

- [ ] **Step 4: Run the smoke unit test and verify GREEN**

Run the same smoke unit test. Expected: pass.

### Task 4: Verification, Audit, Sync, Push

**Files:**
- No new production files unless verification reveals a defect.

- [ ] **Step 1: Run the GUI unit suite**

```powershell
python -m unittest -v tests.unit.test_gui
```

Expected: all tests pass.

- [ ] **Step 2: Run compile checks**

```powershell
python -m compileall -q src\quant_robot\gui scripts\run_gui_control_center_audit.py scripts\run_gui_browser_smoke.py
```

Expected: exit code 0.

- [ ] **Step 3: Run project audit**

```powershell
python scripts\run_project_audit.py --json
```

Expected: safety passes and forbidden hits are empty.

- [ ] **Step 4: Restart local GUI and generate browser smoke**

```powershell
python scripts\run_gui.py --host 127.0.0.1 --port 8765
python scripts\run_gui_browser_smoke.py --base-url http://127.0.0.1:8765 --output-dir data\reports\gui_browser_smoke
```

Expected: browser smoke packet status is `passed`.

- [ ] **Step 5: Run independent GUI audit**

```powershell
python scripts\run_gui_control_center_audit.py --output-dir data\reports\gui_control_center_audit
```

Expected: score remains clear and live trading stays disabled.

- [ ] **Step 6: Run sync audit, commit, and push**

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_review
git diff --check
git add docs/superpowers/specs/2026-06-28-gui-workflow-trace-design.md docs/superpowers/plans/2026-06-28-gui-workflow-trace.md src/quant_robot/gui/control_center.py src/quant_robot/gui/static/index.html src/quant_robot/gui/static/app.js src/quant_robot/gui/static/styles.css scripts/run_gui_browser_smoke.py tests/unit/test_gui.py
git commit -m "feat: add gui workflow trace"
git push origin codex/gui-control-center-mvp-20260627
```

Expected: only source, tests, docs, and lightweight scripts are staged and pushed.
