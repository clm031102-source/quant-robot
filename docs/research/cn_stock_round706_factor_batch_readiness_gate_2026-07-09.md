# CN Stock Round706 Factor Batch Readiness Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round706 added a sequential factor-batch readiness gate for CN stock mining. It exists to prevent downstream candidate-plan checks from racing ahead of the local source queue audit, and to make the "can this factor batch start now?" decision reproducible from one command.

This was readiness tooling only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Startup Evidence

- Quant PM startup gate: `ready`; primary market `CN_ETF`; blockers `[]`.
- CN stock factor-mining startup gate: `cleared`.
- Local source queue audit: `blocked`.
- Candidate-plan gate with local source queue: `blocked`.

## New Sequential Gate

Added:

- `src/quant_robot/ops/factor_batch_readiness_gate.py`
- `scripts/run_factor_batch_readiness_gate.py`
- `tests/unit/test_factor_batch_readiness_gate.py`
- `tests/unit/test_factor_batch_readiness_gate_cli.py`

The CLI runs in this order:

1. Build and write the local source queue audit under `<output>/source_queue`.
2. Pass that written source queue JSON into `factor_mining_candidate_plan_gate`, written under `<output>/candidate_plan_gate`.
3. Build and write the combined readiness gate under `<output>`.

This removes the file-order race between source queue generation and candidate-plan validation.

## Real CLI Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --processed-root data\processed --reports-root data\reports --output-dir data\reports\round706_factor_batch_readiness_gate_20260709 --allow-blocked
```

Result:

- Status: `blocked`.
- Source queue status: `blocked`.
- Candidate-plan gate status: `blocked`.
- Source queue active source count: `1`.
- Candidate count: `4`.
- `factor_batch_ready`: `false`.
- `research_screen_allowed`: `false`.
- `portfolio_grid_allowed`: `false`.
- `promotion_allowed`: `false`.
- Next action: `wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight`.

Blockers:

- `source_queue_blocked:no_local_no_provider_source_ready`
- `source_queue_blocked:report_rc_quota_blocked`
- `candidate_plan_gate_blocked:local_source_queue_blocked:no_local_no_provider_source_ready,report_rc_quota_blocked`
- `candidate_plan_gate_blocked:candidate_source_provider_not_allowed:analyst_report_revision`

## Verification

Fresh targeted tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py
```

Result: `4 passed`.

## Decision

Do not run a CN stock factor batch, analyst prescreen, portfolio grid, or promotion check while the combined readiness gate is blocked. After `report_rc` quota resets, rerun the combined readiness gate first. Only if the source queue and candidate-plan gate both clear should the frozen analyst prescreen proceed.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
