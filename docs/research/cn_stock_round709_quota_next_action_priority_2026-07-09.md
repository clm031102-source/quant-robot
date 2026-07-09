# CN Stock Round709 Quota Next Action Priority

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round709 tightened the combined readiness gate's blocked `next_action` priority. When analyst quota preflight is provided and blocked, its own `decision.next_action` now takes precedence over the source queue next action.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `src/quant_robot/ops/factor_batch_readiness_gate.py`
- `tests/unit/test_factor_batch_readiness_gate.py`

Behavior:

- If readiness is clear, next action remains `run_frozen_candidate_prescreen`.
- If quota preflight is blocked and provides a next action, the combined gate uses that quota next action.
- Otherwise, the gate falls back to the source queue next action or `review_factor_batch_readiness_blockers`.

## Real CLI Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --processed-root data\processed --reports-root data\reports --quota-report-root data\reports --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=quota pack not imported on office_desktop round709" --quota-pack-machine-note "laptop=quota pack not imported on office_desktop round709" --output-dir data\reports\round709_factor_batch_readiness_required_quota_pack_20260709 --allow-blocked
```

Result:

- Status: `blocked`.
- Provider quota preflight status: `blocked`.
- `factor_batch_ready`: `false`.
- Next action: `collect_required_quota_pack_evidence`.
- Blockers include:
  - `provider_quota_preflight_blocked:daily_provider_request_budget_exhausted`
  - `provider_quota_preflight_blocked:missing_required_quota_pack_machines`
  - `source_queue_blocked:no_local_no_provider_source_ready`
  - `source_queue_blocked:report_rc_quota_blocked`

## Verification

Red test was first observed failing because the combined gate still used the source queue next action when quota preflight was blocked. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_analyst_report_quota_pack.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py -q
```

Result: `36 passed`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall src\quant_robot\ops\factor_batch_readiness_gate.py
```

Result: passed.

## Decision

For quota-blocked analyst-report work, follow the quota preflight next action first. If required quota-pack machines are missing, collect/import valid quota-pack evidence before any provider-backed analyst cache or frozen prescreen.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
