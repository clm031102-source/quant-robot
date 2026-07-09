# CN Stock Round705 Candidate Plan Source Queue Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round705 hardened the pre-mining candidate-plan gate so it can consume the Round704/Round705 local source queue audit before any candidate screening. The purpose is to prevent a complete-looking candidate plan from bypassing the current source queue decision when `report_rc` quota is blocked or when a source family is hibernated/closed.

This was gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Current Evidence

- Quant PM startup gate: `ready`; primary market `CN_ETF`; blockers `[]`.
- CN stock factor-mining startup gate: `cleared`.
- July 2024 analyst-report quota preflight: `blocked`.
- Quota blocker: `daily_provider_request_budget_exhausted`.
- Counted provider request windows: `2`.
- Remaining request windows: `0`.
- Local source queue audit: `blocked`.
- Local source queue blockers:
  - `no_local_no_provider_source_ready`
  - `report_rc_quota_blocked`

## Gate Change

`factor_mining_candidate_plan_gate` now accepts an optional local source queue audit packet.

Code paths:

- `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`
- `scripts/run_factor_mining_candidate_plan_gate.py`
- `tests/unit/test_factor_mining_candidate_plan_gate.py`
- `tests/unit/test_factor_mining_candidate_plan_gate_cli.py`

New checks:

- If the local source queue audit is blocked, the candidate-plan gate adds `local_source_queue_blocked:<blockers>`.
- Active candidates must declare `source_id` when a local source queue audit is provided.
- Candidate `source_id` must exist in the queue packet.
- Candidate source status must be `active_source_accumulation`.
- Candidate source evidence must be present.
- Provider-required sources require `provider_factor_batch_allowed == true`.
- No-provider sources require `no_provider_factor_batch_allowed == true`.

The gate summary now records `local_source_queue_status`, and candidate rows record `source_id`, `source_queue_status`, and `source_queue_allowed`.

## Analyst Candidate Plan Alignment

Updated the historical analyst-report candidate plan:

- `configs/factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json`

Each of the four analyst candidates now declares:

```json
"source_id": "analyst_report_revision"
```

This makes the gate failure source-aware instead of only reporting a missing mapping.

## Real CLI Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --local-source-queue-audit data\reports\round705_local_source_queue_audit_20260709\cn_stock_local_source_queue_audit.json --gate-stage discovery --output-dir data\reports\round705_analyst_candidate_plan_gate_with_source_queue_20260709 --allow-blocked
```

Result:

- Status: `blocked`.
- Candidate count: `4`.
- Complete control areas: `9 / 9`.
- Local source queue status: `blocked`.
- Research screen allowed: `false`.
- Portfolio grid allowed: `false`.
- Promotion allowed: `false`.
- Blockers:
  - `local_source_queue_blocked:no_local_no_provider_source_ready,report_rc_quota_blocked`
  - `candidate_source_provider_not_allowed:analyst_report_revision`

This is the intended behavior: the analyst plan has complete controls, but the source queue and provider quota do not allow new screening today.

## Verification

Fresh targeted tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_factor_mining_candidate_plan_gate.py tests\unit\test_factor_mining_candidate_plan_gate_cli.py tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py
```

Expected passing set: candidate-plan gate source queue integration plus the local source queue audit.

## Decision

Do not run analyst candidate screening, no-provider factor batches, portfolio grids, or promotion checks while the local source queue is blocked and `report_rc` quota is exhausted. After quota resets, rerun the source queue audit and candidate-plan gate with the local source queue packet before any July 2024 analyst monthly cache or frozen prescreen.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
