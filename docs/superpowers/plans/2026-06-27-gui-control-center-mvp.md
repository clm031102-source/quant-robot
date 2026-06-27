# GUI Control Center MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-screen control center to the existing local GUI so users can see current work, backtest parameters, backtest method, result slots, artifacts, paper boundary, and live-disabled status.

**Architecture:** Add a focused Python snapshot builder under `src/quant_robot/gui/control_center.py`, expose it through the existing standard-library HTTP app, and render it in the current static Dashboard. Keep all behavior local and research-to-paper only.

**Tech Stack:** Python standard library HTTP server, vanilla HTML/CSS/JavaScript, unittest, existing project audit script.

---

### Task 1: Control Center Snapshot

**Files:**
- Create: `src/quant_robot/gui/control_center.py`
- Modify: `tests/unit/test_gui.py`

- [ ] **Step 1: Write the failing unit test**

Add a test that imports `build_control_center_snapshot` and asserts the snapshot has the required operator fields:

```python
def test_control_center_snapshot_exposes_work_backtest_method_and_safety(self):
    result = build_control_center_snapshot(repo_root=Path.cwd(), active_goal="Build GUI control center")
    self.assertEqual(result["stage"], "gui_control_center")
    self.assertIn("work", result)
    self.assertIn("backtest", result)
    self.assertIn("method", result)
    self.assertIn("results", result)
    self.assertIn("artifacts", result)
    self.assertIn("safety", result)
    self.assertIn("automation", result)
    self.assertFalse(result["safety"]["live_trading_allowed"])
    self.assertGreaterEqual(len(result["method"]["steps"]), 6)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiSnapshotTests.test_control_center_snapshot_exposes_work_backtest_method_and_safety
```

Expected: failure because `quant_robot.gui.control_center` or `build_control_center_snapshot` does not exist.

- [ ] **Step 3: Implement the minimal snapshot builder**

Create `control_center.py` with a pure local function that returns JSON-safe dictionaries. Use `subprocess.run(["git", "branch", "--show-current"])` defensively for branch detection and `Path.exists()` for lightweight artifact checks.

- [ ] **Step 4: Run the test and verify GREEN**

Run the same unit test. Expected: pass.

### Task 2: HTTP Endpoint

**Files:**
- Modify: `src/quant_robot/gui/app.py`
- Modify: `tests/unit/test_gui.py`

- [ ] **Step 1: Write the failing HTTP test**

Extend the GUI HTTP test to assert:

```python
control = _read_json(f"{base_url}/api/control/status")
self.assertEqual(control["stage"], "gui_control_center")
self.assertIn("backtest", control)
self.assertIn("method", control)
self.assertFalse(control["safety"]["live_trading_allowed"])
```

- [ ] **Step 2: Run the HTTP test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiHttpTests.test_http_app_serves_index_snapshot_and_demo_workflows
```

Expected: failure or 404 for `/api/control/status`.

- [ ] **Step 3: Add the route**

Import `build_control_center_snapshot` in `app.py` and route `GET /api/control/status` to it.

- [ ] **Step 4: Run the HTTP test and verify GREEN**

Run the same test. Expected: pass.

### Task 3: Dashboard Control Center UI

**Files:**
- Modify: `src/quant_robot/gui/static/index.html`
- Modify: `src/quant_robot/gui/static/app.js`
- Modify: `src/quant_robot/gui/static/styles.css`
- Modify: `tests/unit/test_gui.py`

- [ ] **Step 1: Write failing static asset assertions**

Add test assertions for these markers:

```python
self.assertIn("control-center-board", html)
self.assertIn("control-work-status", html)
self.assertIn("control-backtest-status", html)
self.assertIn("control-method-steps", html)
self.assertIn("control-safety-boundary", html)
self.assertIn("/api/control/status", app_js)
self.assertIn("renderControlCenter", app_js)
```

- [ ] **Step 2: Run the HTTP static test and verify RED**

Run:

```powershell
python -m unittest -v tests.unit.test_gui.GuiHttpTests.test_http_app_serves_index_snapshot_and_demo_workflows
```

Expected: failure because the new control-center IDs and JavaScript function are missing.

- [ ] **Step 3: Add Dashboard markup**

Insert a first Dashboard section with the required IDs. Keep it compact and scan-friendly.

- [ ] **Step 4: Add JavaScript loading and rendering**

Add `state.controlCenter`, `loadControlCenter()`, and `renderControlCenter()`. Call `await loadControlCenter()` during startup and update result slots from existing `state.research` and `state.paper` when available.

- [ ] **Step 5: Add CSS**

Add grid and status styles for the control center. Keep responsive wrapping and avoid fixed text overflow.

- [ ] **Step 6: Run the HTTP static test and verify GREEN**

Run the same HTTP test. Expected: pass.

### Task 4: Verification And Startup

**Files:**
- No production file changes unless verification finds a defect.

- [ ] **Step 1: Run GUI tests**

```powershell
python -m unittest -v tests.unit.test_gui
```

Expected: all GUI tests pass.

- [ ] **Step 2: Run project audit**

```powershell
python scripts\run_project_audit.py --json
```

Expected: audit exits 0 and reports no forbidden token/data/broker files.

- [ ] **Step 3: Start local GUI**

```powershell
python scripts\run_gui.py --host 127.0.0.1 --port 8765
```

Expected: server prints the local URL and research-only boundary. If port 8765 is occupied, use another free local port.

- [ ] **Step 4: Smoke-check HTTP responses**

Open or fetch:

```text
http://127.0.0.1:<port>/
http://127.0.0.1:<port>/api/control/status
```

Expected: the page contains the control-center board and the API returns `stage == gui_control_center`.

- [ ] **Step 5: Commit the verified work**

Stage only source, tests, docs, and lightweight project files. Do not stage `data/raw`, `data/processed`, `data/reports`, logs, tokens, broker credentials, account data, or generated large outputs.
