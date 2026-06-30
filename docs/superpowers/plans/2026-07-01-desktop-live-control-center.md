# Desktop Live Control Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local Quant Robot GUI usable as a beginner-friendly desktop control center while preserving the project boundary: research-to-paper only, no broker connection, no account read, no automatic order.

**Architecture:** Keep the existing Python/Tkinter desktop shell as the Windows entrypoint and the browser GUI as the main control surface. Add explicit same-parameter paper rehearsal gates before any manual broker review ticket is shown, so the app can explain "what to do today" without implying that a signal is an executable order.

**Tech Stack:** Python stdlib Tkinter/HTTP server, existing `quant_robot.gui.app` static frontend, existing daily trade advisory API, Python `unittest`.

---

### Task 1: Preserve The Desktop Entry Point

**Files:**
- Modify: `src/quant_robot/gui/desktop_app.py`
- Modify: `scripts/install_quant_robot_desktop_shortcuts.py`
- Test: `tests/unit/test_gui.py`

- [ ] **Step 1: Write the failing test**

Add assertions that the desktop shell and generated shortcuts expose the beginner workflow in this order: today action, Top3 signal, same-parameter paper rehearsal, manual trading check, factor leaderboard, post-close journal, logs.

Run:

```powershell
python -m unittest tests.unit.test_gui.GuiDesktopAppTests
```

Expected before implementation: FAIL if any required beginner label, deep link, or safety boundary is missing.

- [ ] **Step 2: Implement the minimal desktop copy/launcher changes**

Update the desktop copy and shortcut output only where the tests require it. Keep generated launchers local, no tokens, no broker/account/order fields.

- [ ] **Step 3: Verify desktop tests**

Run:

```powershell
python -m unittest tests.unit.test_gui.GuiDesktopAppTests
```

Expected: PASS.

### Task 2: Block Manual Broker Tickets Until Same-Parameter Paper Evidence Is Complete

**Files:**
- Modify: `src/quant_robot/ops/daily_trade_advisory.py`
- Modify: `src/quant_robot/gui/static/app.js`
- Test: `tests/unit/test_daily_trade_advisory.py`
- Test: `tests/unit/test_gui.py`

- [ ] **Step 1: Write the failing backend test**

Add a test proving that `manual_broker_handoff` does not expose `copyable_tickets` until same-parameter Top3 paper evidence is declared ready. The handoff should report `same_parameter_paper_required=true`, `copyable_tickets_masked_until_same_parameter_paper=true`, and a blocked ticket count.

Run:

```powershell
python -m unittest tests.unit.test_daily_trade_advisory.DailyTradeAdvisoryTests.test_manual_broker_handoff_masks_copyable_tickets_until_same_parameter_paper
```

Expected before implementation: FAIL because copyable tickets are currently shown whenever pretrade readiness is yellow and manual tickets exist.

- [ ] **Step 2: Write the failing frontend static test**

Add a static GUI test proving the frontend has a dedicated same-parameter manual review gate helper and renders a blocker instead of ticket/copy/export controls when the Top3 paper completion is incomplete.

Run:

```powershell
python -m unittest tests.unit.test_gui.GuiDesktopAppTests.test_daily_page_exposes_trading_system_blueprint_panel
```

Expected before implementation: FAIL because the helper names and blocker text are absent.

- [ ] **Step 3: Implement backend masking**

In `_build_manual_broker_handoff`, build raw manual review tickets but expose them only when same-parameter paper evidence is ready. Until then, return an empty `copyable_tickets` list, keep `order_placement_allowed=false`, and include the masked count plus the reason `same_parameter_paper_required_before_manual_tickets`.

- [ ] **Step 4: Implement frontend masking**

Add a frontend helper that reads `daily_same_parameter_paper_rehearsal.recommended_requests`, calls `sameParameterPaperCompletion`, and masks manual broker ticket cards, ticket table, copy cards, export, daily manual trading session previews, and real-world handoff previews until all Top3 same-parameter receipts are matched.

- [ ] **Step 5: Verify focused tests**

Run:

```powershell
python -m unittest tests.unit.test_daily_trade_advisory tests.unit.test_gui.GuiDesktopAppTests
```

Expected: PASS.

### Task 3: Full Verification And Sync

**Files:**
- Use existing scripts only.

- [ ] **Step 1: Compile Python**

Run:

```powershell
python -m compileall src\quant_robot tests\unit\test_gui.py tests\unit\test_daily_trade_advisory.py
```

Expected: exit code 0.

- [ ] **Step 2: Run GUI unit tests**

Run:

```powershell
python -m unittest tests.unit.test_gui tests.unit.test_daily_trade_advisory
```

Expected: PASS.

- [ ] **Step 3: Run project audit**

Run:

```powershell
python scripts\run_project_audit.py
```

Expected: exit code 0.

- [ ] **Step 4: Safe sync to cloud**

Run:

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_review
python scripts\sync_project.py --machine office_desktop --task factor_review --execute --push
```

Expected: no forbidden data/token/broker/account/order paths, commit created, branch pushed.

### Self-Review

- Spec coverage: covers desktop shell, beginner workflow, same-parameter paper gate, manual ticket masking, verification, and sync.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: backend field names are `same_parameter_paper_required`, `same_parameter_paper_ready`, `copyable_tickets_masked_until_same_parameter_paper`, `blocked_copyable_ticket_count`, and `manual_ticket_mask_reason`.
