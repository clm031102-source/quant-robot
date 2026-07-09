# CN Stock Round744 Analyst Source Extension Priority Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round744 converted the current analyst-report revision evidence into a repeatable source-extension priority gate.

This round read the Round743 non-LPR source gate and the Round729 analyst-report local prescreen. It did not call a provider, download data, cache a new analyst month, run a fresh factor batch, run a portfolio grid, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Implemented Gate

New files:

- `src/quant_robot/ops/analyst_report_source_extension_priority_gate.py`
- `scripts/run_analyst_report_source_extension_priority_gate.py`
- `tests/unit/test_analyst_report_source_extension_priority_gate.py`
- `tests/unit/test_analyst_report_source_extension_priority_gate_cli.py`

The gate:

- requires `analyst_report_revision` to be selected by the non-LPR source gate;
- reads the frozen analyst prescreen rows;
- ranks rows by IC strength, t-stat, ICIR, multiple-testing significance, and neutralized evidence;
- penalizes insufficient year coverage;
- chooses the next source-extension priority row;
- blocks provider cache until quota clears;
- requires the same frozen prescreen after the next monthly cache;
- keeps formula tuning, window tuning, portfolio grids, promotion, paper signals, final holdout, and live boundaries closed.

## Real Gate Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_source_extension_priority_gate.py --allow-blocked
```

Output: `data/reports/round744_analyst_source_extension_priority_gate_20260709`

Result:

- Status: `blocked_waiting_for_quota`
- Priority source: `analyst_report_revision`
- Priority factor: `analyst_target_upside_60`
- Priority horizon: 5
- Priority score: 4.4664
- Latest report date: 2024-06-30
- Provider cache allowed now: false
- Cache next month after quota reset: true
- Frozen prescreen required: true
- Formula tuning allowed: false
- Window tuning allowed: false
- Portfolio grid allowed: false
- Promotion allowed: false
- Live boundary allowed: false

Blockers:

- `provider_quota_preflight_blocked`
- `priority_row_year_coverage_below_gate`

Priority rows:

| Rank | Factor | H | Score | IC | t | ICIR | FDR | Size t | Industry t | Years | Status |
|---:|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| 1 | `analyst_target_upside_60` | 5 | 4.4664 | 0.1511 | 3.74 | 0.577 | yes | 2.91 | 14.76 | 1 | priority pending year coverage |
| 2 | `analyst_target_upside_60` | 20 | 3.2581 | 0.0860 | 2.75 | 0.425 | yes | 1.77 | 13.59 | 1 | priority pending year coverage |
| 3 | `analyst_revision_target_composite_90` | 20 | 2.7378 | 0.0510 | 2.51 | 0.379 | yes | 2.06 | 26.24 | 1 | priority pending year coverage |
| 4 | `analyst_revision_target_composite_90` | 5 | 2.2605 | 0.0432 | 2.32 | 0.350 | yes | 1.32 | 18.88 | 1 | priority pending year coverage |

The remaining EPS/NP revision rows are watch-only because they are not FDR-significant after multiple-testing control.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_source_extension_priority_gate.py tests\unit\test_analyst_report_source_extension_priority_gate_cli.py
```

Result: `5 passed`.

## Decision

After quota reset, the next analyst source-extension run should cache the next monthly `report_rc` window and rerun the same frozen analyst prescreen, with `analyst_target_upside_60` horizon 5 as the priority diagnostic row.

Do not tune the target-upside formula, change windows, run a portfolio grid, run promotion, generate paper/live signals, or read final holdout from this evidence. The current evidence is still one-year coverage with zero research leads.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
