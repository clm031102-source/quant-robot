# CN Stock Round708 Quota Preflight Readiness Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round708 connected the sequential factor-batch readiness gate to the existing analyst-report quota preflight. This removes the need to rely on a naked manual provider switch when deciding whether the analyst-report path can proceed.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `scripts/run_factor_batch_readiness_gate.py`
- `src/quant_robot/ops/factor_batch_readiness_gate.py`
- `tests/unit/test_factor_batch_readiness_gate.py`
- `tests/unit/test_factor_batch_readiness_gate_cli.py`

New behavior:

- `--quota-report-root` runs `analyst_report_quota_preflight` under `<output>/analyst_quota_preflight`.
- When quota preflight is provided, `decision.request_allowed` is the authoritative provider-readiness switch.
- A blocked quota preflight overrides `--provider-request-allowed`.
- The combined readiness packet records `provider_quota_preflight_status` and adds `provider_quota_preflight_blocked:<blocker>` when quota evidence blocks.
- If no quota root is provided, the previous manual `--provider-request-allowed` behavior remains available for controlled smoke tests.

## Real CLI Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --processed-root data\processed --reports-root data\reports --quota-report-root data\reports --output-dir data\reports\round708_factor_batch_readiness_quota_preflight_20260709 --allow-blocked
```

Result:

- Status: `blocked`.
- Provider quota preflight status: `blocked`.
- Source queue status: `blocked`.
- Candidate-plan gate status: `blocked`.
- Candidate count: `4`.
- `factor_batch_ready`: `false`.
- `research_screen_allowed`: `false`.
- Next action: `wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight`.

Blockers:

- `provider_quota_preflight_blocked:daily_provider_request_budget_exhausted`
- `source_queue_blocked:no_local_no_provider_source_ready`
- `source_queue_blocked:report_rc_quota_blocked`
- `candidate_plan_gate_blocked:local_source_queue_blocked:no_local_no_provider_source_ready,report_rc_quota_blocked`
- `candidate_plan_gate_blocked:candidate_source_provider_not_allowed:analyst_report_revision`

## Verification

Red tests were first observed failing for the missing quota-readiness API and CLI flags, then passed after implementation.

Full related gate-chain verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_analyst_report_quota_pack.py tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py tests\unit\test_factor_mining_candidate_plan_gate.py tests\unit\test_factor_mining_candidate_plan_gate_cli.py -q
```

Result: `59 passed`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall src\quant_robot\ops\factor_batch_readiness_gate.py scripts\run_factor_batch_readiness_gate.py src\quant_robot\ops\analyst_report_quota_preflight.py
```

Result: passed.

## Decision

Before any next analyst-report frozen prescreen, run the combined readiness gate with `--quota-report-root` evidence. If quota preflight is blocked, do not pass `--provider-request-allowed` as an override; wait for real quota reset or import valid quota-pack evidence.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
