# CN Stock Round711 Factor Batch Readiness Validator

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round711 added a reusable validator for combined factor-batch readiness packets. Downstream factor-screen or prescreen entrypoints can use this validator to refuse stale, blocked, or live-boundary-violating readiness evidence before any expensive or provider-sensitive work begins.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `src/quant_robot/ops/factor_batch_readiness_gate.py`
- `tests/unit/test_factor_batch_readiness_gate.py`

New helper:

```python
validate_factor_batch_readiness_gate_packet(packet_path, require_generated_today=True, context="CN stock factor batch")
```

Validation rules:

- Packet path must exist.
- `generated_at` must be today by default.
- Top-level `status` must be `ready`.
- `decision.factor_batch_ready` must be `true`.
- `live_boundary_allowed` must be `false`.

## Verification

Red test was first observed failing because the validator did not exist. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py -q
```

Result: `9 passed`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall src\quant_robot\ops\factor_batch_readiness_gate.py
```

Result: passed.

## Decision

Future factor-screen or analyst prescreen entrypoints should validate the combined readiness packet before starting. A blocked readiness packet should stop the run with its blocker evidence instead of allowing local scripts to proceed from partial gates.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
