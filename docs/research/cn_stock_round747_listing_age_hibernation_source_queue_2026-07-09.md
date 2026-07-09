# CN Stock Round747 Listing-Age Hibernation Source Queue

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round747 updated the local source queue so the Round259 listing-age and board-structural family is explicitly hibernated.

This round did not call a provider, download data, run factor IC screens, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Why

Round259 tested A-share listing-age and board-permission structural constraints as a non-daily-basic, non-forecast, non-moneyflow, non-public-technical family. The long-cycle residual screen produced 0 residual research leads and 0 portfolio candidates after industry, size, liquidity, volatility, and yearly-stability controls.

Without an explicit source-queue row, this cheap local metadata family could be accidentally rediscovered as a no-provider candidate.

## Change

Added `listing_age_board_structural` to the CN stock local source queue as:

- Status: `hibernated`
- Provider required: false
- Allowed next action: `use_listing_age_and_board_as_risk_control_not_alpha_source`
- Blocked actions:
  - `listing_age_threshold_tuning`
  - `board_permission_direct_rank`
  - `fresh_listing_sign_flip`
  - `sign_flip_after_residual_collapse`
  - `portfolio_grid`
- Latest evidence: `round259_listing_age_board_zero_residual_leads`

## Real Source Queue Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round747_local_source_queue_listing_age_hibernation_20260709
```

Result:

- Status: `blocked`
- Source count: 16
- Active source count: 1
- Evidence-ready active source count: 1
- Local-prescreen-ready source count: 1
- No-provider-ready source count: 0
- Provider-ready source count: 1
- Hibernated or closed source count: 13
- Blockers:
  - `no_local_no_provider_source_ready`
  - `report_rc_quota_blocked`

Listing-age row:

- Status: `hibernated`
- Evidence present: true
- Matched report: `data\reports\round259_listing_age_board_full_core_20260626`
- Local prescreen allowed: false

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py -q
```

Result: `8 passed`.

## Decision

Do not revive listing-age or board-permission structural variables through threshold tuning, sign flips, direct rankings, or portfolio grids. They remain useful as risk/control context, not as an active alpha source. The queue still has no no-provider-ready factor batch source; the only active path remains analyst-report revision after quota and priority gates clear.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
