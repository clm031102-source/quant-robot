# CN Stock Round507 Analyst Report Quota Preflight

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 4 after the Round504 review-agent baseline. This round added a local preflight for Tushare `report_rc` analyst-report cache requests. It does not call Tushare and does not create processed factor inputs.

## Round Objective

Round506 concluded that 2026-07-05 already had two successful monthly `report_rc` requests and should not blindly attempt a third request. Round507 converted that manual rule into a small repeatable tool:

- Scan local `tushare_analyst_report_cache.json` reports.
- Count same-day provider request windows for `tushare_report_rc`.
- Ignore resumed `cached` windows and reports from other dates.
- Block when the local same-day count reaches the configured daily budget.
- Block immediately when a same-day provider rate-limit row is observed.

## Added Tooling

New files:

- `src/quant_robot/ops/analyst_report_quota_preflight.py`
- `scripts/run_analyst_report_quota_preflight.py`
- `tests/unit/test_analyst_report_quota_preflight.py`

Default behavior:

- Reads local report roots only.
- Default report root: `data/reports`.
- Default max daily requests: `2`.
- Writes `analyst_report_quota_preflight.json` and `.md` to an output directory.
- Keeps `live_boundary_allowed=false`.

## Test-First Evidence

The first test run failed before implementation because the module did not exist:

```text
ModuleNotFoundError: No module named 'quant_robot.ops.analyst_report_quota_preflight'
```

After adding the minimal implementation, the focused unit test passed:

```text
4 passed in 0.18s
```

## Real Local Preflight

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_quota_preflight.py --report-root data\reports --target-date 2026-07-05 --max-daily-requests 2 --output-dir data\reports\round507_analyst_report_quota_preflight_20260705
```

Result:

- Status: `blocked`
- Request allowed: false
- Blockers: `daily_provider_request_budget_exhausted`
- Cache reports counted: 2
- Counted provider request windows: 2
- Rate-limited windows: 0
- Remaining request windows: 0

Counted windows:

| Source report | Window | Status |
| --- | --- | --- |
| `data/reports/round504_analyst_report_revision_cache_202402_20260705/tushare_analyst_report_cache.json` | 20240201..20240229 | ok |
| `data/reports/round505_analyst_report_revision_cache_202403_20260705/tushare_analyst_report_cache.json` | 20240301..20240331 | ok |

Generated preflight outputs stay under ignored `data/reports`.

## Decision

Do not attempt April 2024 `report_rc` on 2026-07-05. The new preflight turns the Round506 manual quota judgment into a reusable command that should be run before every future analyst-report cache attempt.

Allowed next action after quota reset:

1. Run the startup gates.
2. Run the analyst-report quota preflight for the current date.
3. Cache April 2024 only if the preflight returns `request_allowed=true`.
4. Rerun the same frozen January-April prescreen.
5. If January-April still has zero research leads or zero multiple-testing leads, run a family review and rotate to a new PIT source candidate plan.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
