# GUI Workflow Trace Design

## Goal

Add an operator-visible workflow trace to the Quant Robot GUI control center so the first screen clearly answers what is active now, what will run next, which command or endpoint performs it, where evidence is recorded, and why live trading remains blocked.

## Context

The current control center already exposes work context, run queue, execution plan, startup health, backtest provenance, result evidence, release readiness, audit packets, and the live-disabled boundary. The remaining operator gap is continuity: those panels are useful but separated, so a user still has to mentally connect startup checks, research backtest, advisory signals, paper simulation, verification, audit, publish, and live blocking.

## Recommended Approach

Extend the existing local GUI with a pure backend `workflow_trace` snapshot and a compact frontend panel. This keeps the GUI dependency-light, testable, and aligned with the existing `/api/control/status` contract.

Alternatives considered:

- Build a native desktop shell: useful later, but it would spend this iteration on packaging instead of operator transparency.
- Add a separate dashboard framework: faster for charts, but it creates a second UI surface that can drift from the existing local console.

## Scope

This iteration adds:

- A `workflow_trace` object in `build_control_center_snapshot()`.
- A `gui_workflow_trace` stage with summary fields for current workflow, current status, next endpoint, evidence key, paper-only boundary, live-trading allowance, and row counts.
- Trace rows for startup health, research backtest, result evidence, signal snapshot, paper simulation, verification pack, audit packet, publish branch, and live boundary.
- A dashboard panel with id `control-workflow-trace`.
- Frontend renderer `renderWorkflowTrace()`.
- Browser smoke coverage for the new API contract and DOM/JS/CSS hooks.

Out of scope:

- Broker connection.
- Account read.
- Order placement.
- Long-running background job execution.
- New packaged desktop installer.

## Data Contract

`workflow_trace` is JSON-safe and local-only:

```python
{
    "stage": "gui_workflow_trace",
    "summary": {
        "current_workflow": "research_backtest",
        "current_status": "ready_to_run",
        "next_endpoint": "/api/research?...",
        "evidence_storage_key": "quant_robot.gui.execution_receipts.v1",
        "paper_only": True,
        "live_trading_allowed": False,
        "steps": 9,
        "blocked": 1,
    },
    "rows": [
        {
            "trace_id": "research_backtest",
            "label": "Run CN_ETF research backtest",
            "status": "active",
            "source_workflow": "research_backtest",
            "command": "GET /api/research?...",
            "endpoint": "/api/research?...",
            "evidence": "Metrics appear in result slots and execution receipts.",
            "next_action": "Run research before signal and paper workflows.",
        }
    ],
}
```

## UI Design

The panel is placed near the execution plan because it is the bridge between plan and evidence. It uses existing compact list styling and a dedicated `workflow-trace-list` class for scroll height. Rows are color-coded through existing `ok`, `warn`, and `danger` classes:

- `active`, `queued`, `ready`, `required`, `packet_required`, `publish_ready`: operational states.
- `blocked`: live trading handoff, displayed as a deliberate safety boundary.

## Testing

Required tests:

- Unit snapshot test asserts `workflow_trace` exists, has `stage == gui_workflow_trace`, exposes research, paper, verification, audit, publish, and live-boundary trace IDs, and keeps `live_trading_allowed == False`.
- HTTP/static test asserts `control-workflow-trace`, `/api/control/status`, and `renderWorkflowTrace` exist.
- Browser smoke asserts the API exposes `workflow_trace.rows`, the summary is paper-only, and the stylesheet contains `workflow-trace-list`.

## Acceptance Criteria

The iteration is acceptable when:

- `/api/control/status` exposes the workflow trace.
- The dashboard renders a workflow trace panel on desktop and mobile without horizontal overflow.
- GUI unit tests pass.
- GUI browser smoke passes.
- Project audit and sync audit allow pushing only source, tests, docs, and lightweight files.
