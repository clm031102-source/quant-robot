# CN Stock Round749 Statement Closeout Source Queue Evidence

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round749 tightened the CN stock local source queue evidence semantics for the closed adjacent realized-statement source family.

This round did not call a provider, download data, run factor IC screens, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Change

- `financial_statement_adjacent_realized` now requires real Round691-Round694 report evidence instead of inheriting default `evidence_present=true`.
- Evidence checks now require the glob categories declared by each source definition:
  - if a source declares processed globs and report globs, both categories must match;
  - if a source declares only report globs, report evidence is sufficient;
  - if a source marks evidence as required but declares no globs, evidence is treated as missing.

## Test-Driven Check

The new unit test first failed because `financial_statement_adjacent_realized` reported evidence as present even when no Round691-Round694 report directory existed.

Focused green check:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py -q
```

Result: `9 passed`.

## Real Source Queue Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round749_local_source_queue_statement_closeout_evidence_20260709
```

Result:

- Status: `blocked`
- Source count: 16
- Active source count: 1
- Evidence-ready active source count: 1
- Local-prescreen-ready active source count: 1
- No-provider-ready source count: 0
- Provider-ready source count: 1
- Hibernated or closed source count: 13
- Missing required evidence count: 0
- Blockers:
  - `no_local_no_provider_source_ready`
  - `report_rc_quota_blocked`

Statement closeout evidence matched:

- `data\reports\round691_financial_reporting_timeliness_residual_ic_shape_prescreen_20260709`
- `data\reports\round692_pead_gap_reversal_source_repair_residual_prescreen_20260709`
- `data\reports\round693_statement_working_capital_pressure_residual_prescreen_20260709`
- `data\reports\round694_statement_capital_structure_efficiency_residual_prescreen_20260709`

## Readiness Recheck

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --output-dir data\reports\round749_factor_batch_readiness_after_statement_closeout_evidence_20260709 --quota-report-root data\reports --quota-target-date 2026-07-09 --allow-blocked
```

Result:

- Status: `blocked`
- Source queue source count: 16
- Source queue active source count: 1
- Source queue hibernated/closed source count: 13
- Source queue no-provider-ready source count: 0
- Research screen allowed: false
- Portfolio grid allowed: false
- Promotion allowed: false

Blockers remained:

- `provider_quota_preflight_blocked:daily_provider_request_budget_exhausted`
- `source_queue_blocked:no_local_no_provider_source_ready`
- `source_queue_blocked:report_rc_quota_blocked`
- `candidate_plan_gate_blocked:local_source_queue_blocked:no_local_no_provider_source_ready,report_rc_quota_blocked`
- `candidate_plan_gate_blocked:candidate_source_provider_not_allowed:analyst_report_revision`

## Decision

The source queue now has stronger evidence traceability for the closed realized-statement family. This does not create a no-provider factor-batch path and does not change the active analyst-report revision dependency on report_rc quota reset plus year-coverage accumulation.

Do not revive Round691-Round694 adjacent statement families through sign flips, direct formula mutation, same-parameter replay, portfolio grids, or promotion gates.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
