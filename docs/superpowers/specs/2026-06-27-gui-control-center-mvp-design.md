# GUI Control Center MVP Design

## Goal

Upgrade the existing local Quant Robot GUI into a control-center style console that makes the current work, selected backtest, backtest method, result metrics, logs, report links, and paper/live boundary visible from the first screen.

The first milestone is a local MVP, not a broker application. It must remain research-to-paper only: no broker connection, no account reads, no order placement, and no automatic live trading.

## Context

The project already has a dependency-light local GUI:

- Backend entrypoint: `scripts/run_gui.py`
- HTTP app: `src/quant_robot/gui/app.py`
- Domain service: `src/quant_robot/gui/research_service.py`
- Static frontend: `src/quant_robot/gui/static/index.html`, `app.js`, `styles.css`
- Tests: `tests/unit/test_gui.py`

The GUI already exposes research, backtest, signal snapshot, paper simulation, Daily Ops, promotion, risk, data, and report views. The gap is operator visibility: the user can run workflows, but the first screen does not clearly answer what the agent/project is doing, what is being backtested, how it is being backtested, and why live execution remains blocked.

## Approaches Considered

### Recommended: Extend The Existing Local GUI

Add a small control-center service and a first-screen console section to the current standard-library HTTP app. This preserves the current testable architecture and avoids new packaging risk.

Trade-off: It is still a browser-based local app, not a native desktop executable. A native wrapper can be added later if the local console proves useful.

### Alternative: Build A New Desktop App

Use Electron, Tauri, or a Python desktop framework to build a standalone application.

Trade-off: This would spend the first cycle on packaging, installers, and cross-platform behavior instead of showing the quant workflow clearly.

### Alternative: Build A Separate Streamlit/Gradio App

Use a data-app framework for fast dashboards.

Trade-off: It adds dependencies and creates a second GUI path that can drift away from the existing local console.

## Scope

The MVP adds:

- A `control_center` backend snapshot with branch, machine/task context, active goal summary, safety boundary, current workflow defaults, backtest method explanation, result source pointers, logs, reports, and audit cadence.
- A `/api/control/status` endpoint.
- A visible "Control Center" first-screen block inside the Dashboard.
- Frontend rendering for work status, selected backtest parameters, backtest method, key result fields, paper/live boundary, and audit cadence.
- Unit tests proving the API and static page expose the new console.

Out of scope for this milestone:

- Real broker integration.
- Account balance reads.
- Order routing.
- Automatic live trading.
- Long-running background job execution from the browser.
- Replacing the existing GUI stack.

## Backend Design

Create `src/quant_robot/gui/control_center.py`.

The service exposes:

```python
def build_control_center_snapshot(
    repo_root: str | Path | None = None,
    active_goal: str | None = None,
) -> dict[str, Any]:
    ...
```

The function returns JSON-safe data:

- `stage`: `gui_control_center`
- `status`: `ready`, `blocked`, or `degraded`
- `work`: machine, task, branch, branch policy note, active goal summary
- `backtest`: current source, market, factor, top_n, cost, rebalance interval, execution lag, benchmark, date window
- `method`: ordered steps explaining the backtest path
- `results`: metric names and where live values come from
- `artifacts`: important local report paths and whether each exists
- `safety`: explicit research-to-paper boundary
- `automation`: five-hour audit cadence and expected audit output

The service must be pure and local. It can read lightweight repository files and Git state. It must not read raw market data, processed large data, tokens, account files, or broker credentials.

## HTTP Design

Add this route in `src/quant_robot/gui/app.py`:

```text
GET /api/control/status
```

It returns `build_control_center_snapshot()`. It should use the same JSON sender as the other GUI APIs and no external network calls.

## Frontend Design

The Dashboard becomes the control-center first screen. It keeps the current project metrics, but gains a top "Mission Control" band with:

- Work status: machine/task/branch/goal.
- Backtest now: data source, market, factor, cost, rebalance, date window.
- Method map: data -> factor -> labels -> delayed execution -> portfolio -> costs -> metrics -> artifacts.
- Results board: total return, annualized return, Sharpe, max drawdown, win rate, trade count, benchmark, paper equity.
- Safety boundary: paper allowed only when gates pass; live disabled.
- Audit cadence: every five hours, score and next fixes.

The visual style should stay compact and operational. This is a workstation console, not a landing page.

## Data Flow

```text
Browser Dashboard
  -> /api/control/status
  -> control_center snapshot
  -> repository/git/lightweight artifact existence checks
  -> static UI renders work, backtest, method, results, safety, audit
```

Workflow buttons continue using existing endpoints:

- `/api/research`
- `/api/signals`
- `/api/paper`
- `/api/daily/ops`
- `/api/promotion/ops`

The control center explains these workflows and links their visible state; it does not replace the research engine.

## Error Handling

If Git metadata is unavailable, the snapshot should return `branch: unknown` and keep the GUI usable.

If an artifact is missing, the snapshot should mark it as `missing` and list the local path rather than raising.

If no recent research result is loaded in the browser, frontend result fields show `--` and label the source as "run research or paper workflow".

## Testing

Unit tests must cover:

- `build_control_center_snapshot()` returns stage, work, backtest, method, results, safety, and automation.
- `/api/control/status` returns `stage == gui_control_center`.
- `index.html` contains control-center element IDs.
- `app.js` calls `/api/control/status` and renders the control-center sections.

Verification must include:

- `python -m unittest -v tests.unit.test_gui`
- `python scripts\run_project_audit.py --json`
- Local GUI startup with `python scripts\run_gui.py --host 127.0.0.1 --port <free-port>`
- A browser or HTTP smoke check proving `/` and `/api/control/status` respond.

## Acceptance Criteria

The milestone is complete when:

- The local GUI opens and shows the control center on the first Dashboard screen.
- The user can see current work context, selected backtest parameters, backtest method, result metric slots, log/report entry points, paper boundary, and live-disabled status.
- GUI unit tests pass.
- Project audit passes.
- The GUI can be started locally without new mandatory dependencies.
