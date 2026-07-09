# CN Stock Round746 Calendar Hibernation Source Queue

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round746 updated the local source queue so the old calendar-seasonality direction is explicitly recorded as hibernated after its Round165 cost/capacity failure.

This round did not call a provider, download data, run factor IC screens, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Why

Round164 produced one residual IC lead, `pre_holiday_liquidity_avoidance_5_3`, but Round165 rejected it for tradability. The source queue did not previously include a calendar row, which made the processed/report inventory look less complete and left room for accidental rediscovery under a new name.

## Change

Added `calendar_seasonality` to the CN stock local source queue as:

- Status: `hibernated`
- Provider required: false
- Allowed next action: `do_not_reenter_pre_holiday_or_calendar_windows_after_round165_failure`
- Blocked actions:
  - `pre_holiday_window_tuning`
  - `calendar_bucket_grid`
  - `cost_or_capacity_assumption_rescue`
  - `walk_forward_after_round165_failure`
  - `portfolio_grid`
- Latest evidence: `round163_165_calendar_seasonality_cost_capacity_failure`

## Real Source Queue Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round746_local_source_queue_calendar_hibernation_20260709
```

Result:

- Status: `blocked`
- Source count: 15
- Active source count: 1
- Evidence-ready active source count: 1
- Local-prescreen-ready source count: 1
- No-provider-ready source count: 0
- Provider-ready source count: 1
- Hibernated or closed source count: 12
- Blockers:
  - `no_local_no_provider_source_ready`
  - `report_rc_quota_blocked`

Calendar row:

- Status: `hibernated`
- Evidence present: true
- Matched report: `data\reports\cn_calendar_pre_holiday_cost_capacity_preflight_round165_20260623`
- Local prescreen allowed: false

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py -q
```

Result: `7 passed`.

## Decision

Do not revive the pre-holiday/calendar family through window tuning, bucket grids, cost assumption changes, or walk-forward rescue. The queue still has no no-provider-ready factor batch source. The only active path remains analyst-report revision source extension after the report_rc quota and priority gates clear.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
