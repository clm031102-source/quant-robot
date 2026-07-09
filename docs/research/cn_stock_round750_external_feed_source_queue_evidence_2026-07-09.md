# CN Stock Round750 External Feed Source Queue Evidence

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round750 tightened source-queue evidence traceability for two external-feed directions that are not active alpha sources:

- `northbound_hk_hold_daily`
- `margin_financing`

This round did not call a provider, download data, run factor IC screens, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Change

The local source queue no longer treats these two rows as evidence-present by default.

`northbound_hk_hold_daily` now requires matching report evidence from the HK-hold daily-to-quarterly closeout path:

- `round697_hk_hold_source_symbol_composition_audit_*`
- `round698_hk_hold_quarterly_policy_audit_*`

`margin_financing` now requires matching report evidence from the prior margin/external-feed closeout path:

- `round192_external_margin_credit_prescreen_*`
- `round193_external_margin_credit_neutral_dedup_*`
- `round528_external_feed_coverage_audit_*`

This is a governance hardening change. It does not reopen either family, does not create a local prescreen path, and does not permit a factor batch.

## Test-Driven Check

New failing tests first showed that both source rows reported `evidence_present=true` even when no matching report directories existed.

Focused green check:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py -q
```

Result: `11 passed`.

## Real Source Queue Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round750_local_source_queue_external_feed_evidence_20260709
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

External-feed evidence matches:

| Source | Status | Evidence | Local prescreen |
| --- | --- | --- | --- |
| `northbound_hk_hold_daily` | `source_maintenance_only` | Round697 and Round698 report dirs | false |
| `margin_financing` | `hibernated` | Round192, Round193, and Round528 report dirs | false |

## Readiness Recheck

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --output-dir data\reports\round750_factor_batch_readiness_after_external_feed_evidence_20260709 --quota-report-root data\reports --quota-target-date 2026-07-09 --allow-blocked
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

Do not revive daily northbound HK-hold, old northbound, or margin-financing alpha families from this evidence. HK-hold remains source maintenance / quarterly-state review only. Margin remains hibernated unless a new source or control-role review is preregistered.

The only active factor-mining source remains analyst-report revision accumulation, and it is still blocked from provider extension until the report_rc quota path clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
