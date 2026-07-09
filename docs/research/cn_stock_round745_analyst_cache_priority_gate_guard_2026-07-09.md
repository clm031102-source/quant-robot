# CN Stock Round745 Analyst Cache Priority Gate Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round745 connected the Round744 analyst source-extension priority gate to the `report_rc` cache entrypoint.

This round did not call Tushare, download provider data, create processed analyst-report cache outputs, run a new factor batch, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Change

Provider-backed `scripts/run_tushare_analyst_report_cache.py` now has a second key after quota preflight:

```powershell
--analyst-source-extension-priority-gate <path-to-analyst_report_source_extension_priority_gate.json>
```

When normal quota preflight allows a provider-backed cache attempt, the script now:

- reads the analyst source-extension priority gate;
- writes `analyst_report_cache_priority_gate_guard.json` and `.md` under the cache output directory;
- requires gate status `ready_to_cache_next_month`;
- requires `provider_cache_allowed_now=true`;
- requires the selected source to remain `analyst_report_revision`;
- requires the frozen prescreen route;
- keeps formula tuning, window tuning, portfolio grids, promotion, paper signals, and live boundaries closed;
- exits before constructing `TushareAdapter` or running cache when the guard blocks.

The exceptional `--skip-quota-preflight` cached-replay path remains offline-only and still requires existing processed windows.

## Real Blocked Smoke

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-07-01 --end-date 2024-07-31 --output-dir data\reports\round745_analyst_cache_priority_gate_guard_20260709\cache --processed-output-dir data\processed\round745_analyst_cache_priority_gate_guard_20260709 --request-sleep-seconds 0 --quota-report-root data\reports\round745_analyst_cache_priority_gate_guard_20260709\empty_quota_root --quota-target-date 2026-07-09 --quota-output-dir data\reports\round745_analyst_cache_priority_gate_guard_20260709\quota_preflight --analyst-source-extension-priority-gate data\reports\round744_analyst_source_extension_priority_gate_20260709\analyst_report_source_extension_priority_gate.json
```

Result:

- Quota preflight status: `allowed`.
- Cache priority guard status: `blocked`.
- Priority gate status: `blocked_waiting_for_quota`.
- Priority factor: `analyst_target_upside_60`, horizon 5.
- Blockers:
  - `analyst_source_extension_priority_gate_not_ready`
  - `priority_gate_blocker:provider_quota_preflight_blocked`
  - `priority_gate_blocker:priority_row_year_coverage_below_gate`
  - `provider_cache_not_allowed_now`
- `data\reports\round745_analyst_cache_priority_gate_guard_20260709\cache\analyst_report_cache_priority_gate_guard.json` was written.
- `data\reports\round745_analyst_cache_priority_gate_guard_20260709\cache\tushare_analyst_report_cache.json` was not written.
- `data\processed\round745_analyst_cache_priority_gate_guard_20260709` was not created.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_source_extension_priority_gate.py tests\unit\test_analyst_report_quota_preflight.py -q
```

Result: `26 passed`.

## Decision

After the next `report_rc` quota reset, a provider-backed analyst monthly cache may only continue if both checks pass:

1. Local analyst quota preflight allows the request for the local date.
2. The analyst source-extension priority guard allows the exact Round744-style priority packet.

The next monthly cache target remains source-extension only. After any successful cache, rerun the same frozen analyst prescreen before any further research decision. Do not tune formulas, horizons, lags, report fields, thresholds, or portfolio settings from the current evidence.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
