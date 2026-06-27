# GUI Backtest Gate Design

## Goal

Add a Backtest Gate panel to the Quant Robot GUI control center so the operator can see whether the currently displayed research and paper metrics are strong enough for paper-observation consideration, while live trading remains explicitly blocked.

## Context

The current control center shows the current workflow, backtest parameters, method, provenance, result evidence, workflow trace, release readiness, and audit packets. The remaining usability gap is decision clarity after a result appears: the GUI shows Sharpe, return, drawdown, win rate, trades, benchmark relative return, and paper equity, but it does not yet summarize whether those metrics pass a minimum paper-handoff gate.

## Recommended Approach

Extend `/api/control/status` with a pure `backtest_gate` contract and render it in the existing Mission Control grid. The backend owns the threshold policy and evidence commands. The frontend reads current browser-side `state.research` and `state.paper` metrics and evaluates each gate row as `passed`, `failed`, `awaiting_metric`, or `blocked_expected`.

Alternatives considered:

- Add thresholds only inside the research tab. This would hide the decision from the first-screen control center.
- Create a new paper-trading engine. This is too large for this iteration and would blur the research-to-paper boundary.

## Scope

This iteration adds:

- `backtest_gate` in `build_control_center_snapshot()`.
- Gate rows for Sharpe, total return, annualized return, max drawdown, win rate, trade count, benchmark relative return, paper ending equity, execution receipts, and live boundary.
- A Dashboard panel with id `control-backtest-gate`.
- Frontend renderer `renderBacktestGate()` that evaluates loaded metrics against backend thresholds.
- Browser smoke coverage for the new API, HTML, JS, and CSS hooks.

Out of scope:

- Broker connection.
- Account reading.
- Order placement.
- Automatic live trading.
- Full statistical promotion or walk-forward validation. This panel is a first-screen decision aid, not a replacement for formal validation.

## Threshold Policy

The default panel is intentionally conservative but aligned with the user's tolerance for a larger drawdown when return and Sharpe are high:

- `sharpe >= 1.0`
- `total_return >= 0.0`
- `annualized_return >= 0.05`
- `max_drawdown >= -0.30` because project drawdown metrics are stored as negative values.
- `win_rate >= 0.50`
- `trade_count >= 5`
- `benchmark_relative_return >= 0.0`
- `paper_ending_equity >= paper_request.initial_cash`
- `execution_receipts >= 2` and must match the currently displayed research and paper workflow requests.
- `live_trading_allowed` must remain false.

## Data Contract

`backtest_gate` is local-only and JSON-safe:

```python
{
    "stage": "gui_backtest_gate",
    "summary": {
        "status": "awaiting_research_result",
        "paper_candidate_allowed": False,
        "live_trading_allowed": False,
        "risk_profile": "paper_observation_candidate",
        "next_action": "GET /api/research?...",
        "threshold_count": 10,
    },
    "rows": [
        {
            "gate_id": "sharpe",
            "label": "Sharpe",
            "metric_key": "sharpe",
            "source": "research_metrics",
            "comparator": ">=",
            "threshold": 1.0,
            "severity": "paper_required",
            "status": "awaiting_metric",
            "command": "GET /api/research?...",
            "evidence": "Require Sharpe >= 1.0 before paper-observation consideration.",
        }
    ],
}
```

## UI Design

The panel sits next to result evidence because it answers the next natural question: not just what the metrics are, but whether they meet the paper-handoff floor. Each row shows the metric name, current value or `--`, comparator, threshold, status, and evidence. The header may show `metrics floor only` when all rows pass but the backend still has `paper_candidate_allowed == false`; the GUI must not promote a result beyond the backend safety contract. Live trading is rendered as a positive blocked boundary when disabled.

## Testing

Required tests:

- Unit snapshot test asserts `backtest_gate` exists, has `stage == gui_backtest_gate`, includes threshold rows and live boundary, and keeps live trading disabled.
- HTTP/static test asserts `control-backtest-gate` and `renderBacktestGate` exist.
- Browser smoke asserts the API exposes `backtest_gate.rows`, summary live trading is false, and CSS includes `.backtest-gate-list`.

## Acceptance Criteria

The iteration is acceptable when:

- The Dashboard renders a Backtest Gate panel.
- The panel evaluates current research/paper metrics when they are loaded.
- Missing metrics or stale/unmatched receipts are shown as awaiting, not pass/fail.
- Live trading remains explicitly blocked.
- GUI unit tests, browser smoke, project audit, independent GUI audit, and real browser desktop/mobile checks pass.
