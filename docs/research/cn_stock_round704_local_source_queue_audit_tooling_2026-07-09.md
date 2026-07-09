# CN Stock Round704 Local Source Queue Audit Tooling

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round704 continued the Round703 local-source queue closeout after the analyst-report provider quota remained blocked. The goal was to make the "is there any honest no-provider factor batch left today?" decision repeatable from code instead of re-reading prior reports by hand.

This was source governance only. It did not run provider downloads, generate factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Startup And Quota Evidence

- Quant PM startup gate: `ready`; primary market `CN_ETF`; blockers `[]`; warnings `[]`.
- CN stock factor-mining startup gate: `cleared`; startup gate cleared `true`.
- July 2024 analyst-report quota preflight: `blocked`.
- Quota blocker: `daily_provider_request_budget_exhausted`.
- Counted provider request windows: `2`.
- Remaining request windows: `0`.
- Counted same-day windows: May 2024 cache and June 2024 cache from Round700/Round701.

## New Repeatable Tooling

Added a reusable local source queue audit:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round704_local_source_queue_audit_20260709
```

The tool writes:

- `cn_stock_local_source_queue_audit.json`
- `cn_stock_local_source_queue_audit.md`
- `cn_stock_local_source_queue_rows.csv`

Generated outputs stay under `data/reports` and are not committed.

The code path is:

- `src/quant_robot/ops/cn_stock_local_source_queue_audit.py`
- `scripts/run_cn_stock_local_source_queue_audit.py`
- `tests/unit/test_cn_stock_local_source_queue_audit.py`
- `tests/unit/test_cn_stock_local_source_queue_audit_cli.py`

## Real CLI Result

Round704 real CLI summary:

- Status: `blocked`.
- Source count: `13`.
- Active source count: `1`.
- Evidence-ready active source count: `1`.
- Provider-ready source count: `1`.
- No-provider-ready source count: `0`.
- Hibernated or closed source count: `10`.
- Missing required evidence count: `0`.

Decision:

- `no_provider_factor_batch_allowed`: `false`
- `provider_factor_batch_allowed`: `false`
- Blockers:
  - `no_local_no_provider_source_ready`
  - `report_rc_quota_blocked`
- Next action: `wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight`

## Source Queue Interpretation

The only evidence-ready active source is analyst-report revision accumulation. It requires `report_rc` provider access, so it cannot continue while the same-day quota preflight blocks July 2024 cache work.

Closed or hibernated local directions remain closed for immediate no-provider mining:

- adjacent realized financial-statement formulas;
- forecast/express event formulas;
- share unlock and pledge supply rankings;
- repurchase contextual repair;
- index rebalance passive flow;
- dragon-tiger attention;
- daily northbound `hk_hold` as a daily factor feed;
- margin-style external feed rotations;
- daily-basic direct carry/valuation;
- low-turnover, public technical, and Alpha101 replays.

Official tradeability state and industry breadth remain validation/control context only, not current standalone alpha sources.

## Verification

Fresh targeted tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py
```

Result: `4 passed`.

## Decision

Do not run a no-provider factor batch from the local source queue today. The next valid factor-mining action is still narrow: after `report_rc` quota resets, run the July 2024 analyst-report monthly cache preflight, send at most one provider request only if allowed, then rerun the same frozen analyst prescreen without formula, sign, threshold, portfolio, or holdout tuning.

Until then, valid non-provider work is limited to source-governance tooling, documentation, or validation-only work under the appropriate `factor_validation` task.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
