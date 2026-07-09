# CN Stock Round707 Provider Allowed Readiness Semantics

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round707 tightened the local source queue decision semantics for the provider-allowed path. The default path remains blocked while `report_rc` quota is unavailable; the change only removes a contradictory no-provider blocker when a provider-required active source has evidence and provider requests are explicitly allowed.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Startup Evidence

- Quant PM startup gate: `ready`; primary market `CN_ETF`; blockers `[]`.
- CN stock factor-mining startup gate: `cleared`.
- Default combined readiness gate: `blocked`.
- Provider-allowed combined readiness smoke: `ready`.

## Change

Updated `src/quant_robot/ops/cn_stock_local_source_queue_audit.py` so `no_local_no_provider_source_ready` is a blocker only when neither a no-provider source nor an explicitly allowed provider source can support a batch.

Expected behavior after the change:

- `provider_request_allowed=false`: source queue remains `blocked` with `no_local_no_provider_source_ready` and `report_rc_quota_blocked`.
- `provider_request_allowed=true` with analyst-report evidence present: source queue is `cleared`, `provider_factor_batch_allowed=true`, and blockers are `[]`.
- Missing active-source evidence still blocks before any batch.

## Real CLI Evidence

Default command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --processed-root data\processed --reports-root data\reports --output-dir data\reports\round707_factor_batch_readiness_gate_after_fix_20260709 --allow-blocked
```

Result:

- Status: `blocked`.
- Source queue status: `blocked`.
- Candidate-plan gate status: `blocked`.
- `factor_batch_ready`: `false`.
- Next action: `wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight`.

Provider-allowed smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --processed-root data\processed --reports-root data\reports --output-dir data\reports\round707_factor_batch_readiness_provider_allowed_smoke_20260709 --provider-request-allowed
```

Result:

- Status: `ready`.
- Source queue status: `cleared`.
- Candidate-plan gate status: `research_ready`.
- Candidate count: `4`.
- `factor_batch_ready`: `true`.
- `research_screen_allowed`: `true`.
- `portfolio_grid_allowed`: `false`.
- `promotion_allowed`: `false`.
- Next action: `run_frozen_candidate_prescreen`.
- Blockers: `[]`.

## Verification

Fresh targeted tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_factor_batch_readiness_gate_cli.py
```

Result: `6 passed`.

Full related gate-chain verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py tests\unit\test_factor_mining_candidate_plan_gate.py tests\unit\test_factor_mining_candidate_plan_gate_cli.py -q
```

Result: `28 passed`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall src\quant_robot\ops\cn_stock_local_source_queue_audit.py src\quant_robot\ops\factor_batch_readiness_gate.py src\quant_robot\ops\factor_mining_candidate_plan_gate.py scripts\run_factor_batch_readiness_gate.py
```

Result: passed.

## Decision

Do not treat this as permission to run a provider download today. The provider-allowed flag is a readiness switch for an explicitly approved quota state. Until that state exists, keep using the default readiness gate and remain blocked.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
