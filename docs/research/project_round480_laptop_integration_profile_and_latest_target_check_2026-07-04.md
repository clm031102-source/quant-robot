# Project Round480 Laptop Integration Profile And Latest Target Check

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: check whether the repaired ETF paper-observation target has a newer valid Tushare bar, then add a prewired laptop merged-main verification profile because the target still cannot be extended.

## Progress Snapshot

Estimated project completion after this round: 98%.

The blocker set is unchanged but narrower:

1. laptop must merge the two topic branches into `main`;
2. laptop must run merged-main verification and push `main`;
3. laptop must safe-clean the remote topic branches;
4. paper-only observation must eventually clear the 20-fill policy.

Profit-factor mining remains deferred until those completion conditions are true.

## Startup And Safety Context

| Item | Value |
| --- | --- |
| Machine/task | office_desktop / data_pipeline |
| Quant PM startup gate | `ready` |
| Gate blockers | none |
| Primary market | `CN_ETF` |
| Live-trading boundary | disabled; research-to-paper only |

The office desktop only checked Tushare market data availability and added a local verification profile. No broker connection, live account read, order placement, automatic live trading, `main` merge, or remote branch deletion was performed.

## Latest Target Availability Check

Target ETF: `160615.SZ` / `CN_ETF_XSHE_160615`.

Command shape:

```powershell
python - <<'PY'
from quant_robot.data.adapters.tushare_adapter import TushareAdapter
adapter = TushareAdapter(request_sleep_seconds=0.2)
for date in ["2026-07-03", "2026-07-04", "2026-07-06"]:
    bars = adapter.fetch_etf_daily_by_trade_date(date)
    hit = bars[bars["symbol"].astype(str).eq("160615.SZ")]
    print(date, len(bars), len(hit))
PY
```

Result:

| Date | fund_daily rows | `160615.SZ` rows | Decision |
| --- | ---: | ---: | --- |
| 2026-07-03 | 2,047 | 0 | do not extend required target window |
| 2026-07-04 | 0 | 0 | no target row |
| 2026-07-06 | 0 | 0 | no target row |

The latest clean target date remains 2026-07-02. Do not rerun the observation window through 2026-07-03 unless Tushare later provides a valid `160615.SZ` row or the paper lane is explicitly re-scoped.

## Laptop Integration Profile

Added `scripts/run_checks.py --profile laptop-integration` so the laptop can verify the merged `main` with one command after merging the two topic branches.

The profile contains:

| Step | Command role |
| --- | --- |
| `laptop_integration_unit_tests` | targeted tests for experiment runner, walk-forward, recent refresh, replay, and observation sufficiency |
| `compile_python` | `python -B -m compileall -q scripts src tests` |
| `project_audit` | project audit with output under ignored `data/reports/laptop_integration_project_audit` |
| `laptop_project_sync_audit` | `scripts/sync_project.py --machine laptop --task project_sync` |

Preview command:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration
```

Execution command for the laptop after merging into `main`:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

## Decision

No new paper-observation data can be safely added today because `160615.SZ` is still missing for 2026-07-03. The most useful progress was therefore to make laptop integration verification executable and repeatable. The next machine action is still laptop-owned `project_sync`: merge, run the `laptop-integration` profile on merged `main`, push `main`, then safe-clean topic branches.
