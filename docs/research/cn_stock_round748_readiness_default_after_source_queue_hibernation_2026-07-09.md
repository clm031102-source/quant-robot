# CN Stock Round748 Readiness Default After Source Queue Hibernation

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round748 refreshed the factor-batch readiness chain after Round746 and Round747 added explicit hibernation rows for calendar-seasonality and listing-age/board structural sources.

This round did not call a provider, download data, run factor IC screens, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Startup Gates

Quant PM startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709
```

Result: `status=ready`, primary market `CN_ETF`, blockers `[]`.

Factor-mining startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709 --market CN --asset-type stock --commits-allowed --confirm-start
```

Result: `status=cleared`, startup blockers `[]`, pushes disabled.

## Implemented Changes

- `factor_batch_readiness_gate` now carries source-queue catalog counts:
  - `source_queue_source_count`
  - `source_queue_no_provider_ready_source_count`
  - `source_queue_hibernated_or_closed_source_count`
- `run_cn_stock_non_lpr_orthogonal_source_gate.py` defaults now read Round748 readiness and write a Round748 source-gate output.
- `run_analyst_report_source_extension_priority_gate.py` defaults now read the Round748 non-LPR source gate and write a Round748 priority-gate output.

## Real Readiness Refresh

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --output-dir data\reports\round748_factor_batch_readiness_after_source_queue_hibernation_20260709 --quota-report-root data\reports --quota-target-date 2026-07-09 --allow-blocked
```

Result:

- Status: `blocked`
- Candidate count: 4
- Source queue status: `blocked`
- Provider quota preflight status: `blocked`
- Source queue source count: 16
- Source queue active source count: 1
- Source queue hibernated/closed source count: 13
- Source queue no-provider-ready source count: 0
- Research screen allowed: false
- Portfolio grid allowed: false
- Promotion allowed: false

Blockers:

- `provider_quota_preflight_blocked:daily_provider_request_budget_exhausted`
- `source_queue_blocked:no_local_no_provider_source_ready`
- `source_queue_blocked:report_rc_quota_blocked`
- `candidate_plan_gate_blocked:local_source_queue_blocked:no_local_no_provider_source_ready,report_rc_quota_blocked`
- `candidate_plan_gate_blocked:candidate_source_provider_not_allowed:analyst_report_revision`

## Default Non-LPR Source Gate

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_non_lpr_orthogonal_source_gate.py --allow-blocked
```

Output: `data\reports\round748_non_lpr_source_gate_after_source_queue_hibernation_20260709`

Result:

- Status: `blocked`
- Selected source: `analyst_report_revision`
- Local cached prescreen allowed: true
- Provider request allowed: false
- Full factor batch allowed: false
- Latest report date: 2024-06-30
- Analyst research lead count: 0
- Analyst year-coverage pass count: 0

## Default Analyst Priority Gate

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_source_extension_priority_gate.py --allow-blocked
```

Output: `data\reports\round748_analyst_source_extension_priority_gate_after_source_queue_hibernation_20260709`

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

Blockers:

- `provider_quota_preflight_blocked`
- `priority_row_year_coverage_below_gate`

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_source_extension_priority_gate_cli.py tests\unit\test_analyst_report_source_extension_priority_gate.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_cn_stock_non_lpr_orthogonal_source_gate_cli.py -q
```

Result: `16 passed`.

## Decision

The readiness chain now reflects the expanded source queue. There is still no no-provider-ready factor batch source. The only active path remains analyst-report revision source extension after report_rc quota and the priority guard clear. Do not run fresh factor mining, formula tuning, portfolio grids, promotion gates, paper signals, or live workflows from this readiness state.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
