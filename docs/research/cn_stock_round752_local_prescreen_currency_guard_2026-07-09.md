# CN Stock Round752 Local Prescreen Currency Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round752 tightened the CN stock local source queue so a cached analyst prescreen is not treated as an action to rerun when it already covers the latest locally cached `report_rc` month.

This round did not call a provider, download data, run a new factor IC screen, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Change

`cn_stock_local_source_queue_audit` now records, for the active `analyst_report_revision` source:

- matched analyst prescreen report paths;
- latest local analyst cache period;
- latest analyst prescreen coverage period;
- whether the local prescreen is current against the latest cache.

When the local prescreen is already current and `report_rc` quota remains blocked, the local prescreen next action becomes:

```text
local_prescreen_current_wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight
```

This prevents repeated Jan-Jun 2024 cached prescreen runs when no July 2024 analyst cache exists yet.

## Real Audit Check

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round752_local_source_queue_prescreen_currency_20260709
```

Result:

- Status: `blocked`
- Active source count: 1
- Evidence-ready active source count: 1
- Local-prescreen-ready source count: 1
- No-provider-ready source count: 0
- Provider-ready source count: 1
- Missing required evidence count: 0
- Latest analyst cache period: `202406`
- Latest analyst prescreen period: `202406`
- Local prescreen current: true
- Local prescreen next action: `local_prescreen_current_wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight`
- Blockers:
  - `no_local_no_provider_source_ready`
  - `report_rc_quota_blocked`

## Readiness Next Action Check

The factor-batch readiness gate now preserves the source queue's precise current-prescreen action when the only provider-quota blocker is the daily `report_rc` request budget.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --output-dir data\reports\round753_factor_batch_readiness_prescreen_currency_after_fix_20260709 --quota-report-root data\reports --quota-target-date 2026-07-09 --allow-blocked
```

Result:

- Status: `blocked`
- Research screen allowed: false
- Portfolio grid allowed: false
- Promotion allowed: false
- Next action: `local_prescreen_current_wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight`

## Tests

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py -q
```

Result: `23 passed`.

## Decision

No new factor batch is unlocked. The current analyst prescreen is up to date through June 2024, so the next valid analyst action is to wait for `report_rc` quota readiness, cache the next monthly window, then rerun the same frozen prescreen once. Portfolio grids, promotion, paper signals, and live workflows remain closed.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
