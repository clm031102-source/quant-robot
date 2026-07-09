# CN Stock Round743 Non-LPR Source Gate Default Readiness Refresh

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round743 updated the non-LPR orthogonal source gate CLI default readiness packet from the stale Round729 packet to the latest Round742 readiness rebuild.

This round did not call a provider, download data, run a fresh factor batch, run a portfolio grid, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Change

Updated:

- `scripts/run_cn_stock_non_lpr_orthogonal_source_gate.py`
- `tests/unit/test_cn_stock_non_lpr_orthogonal_source_gate_cli.py`

The default `--readiness-gate` path now points to:

```text
data/reports/round742_factor_batch_readiness_after_lpr_rejection_20260709/factor_batch_readiness_gate.json
```

instead of the older Round729 readiness packet.

## Real Default Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_non_lpr_orthogonal_source_gate.py --allow-blocked --output-dir data\reports\round743_non_lpr_source_gate_default_readiness_refresh_20260709
```

Output: `data/reports/round743_non_lpr_source_gate_default_readiness_refresh_20260709`

Result:

- Status: `blocked`
- Selected source: `analyst_report_revision`
- Source gate selected: true
- Source gate ready: false
- Local cached prescreen allowed: true
- Full factor batch allowed: false
- Provider request allowed: false
- Analyst multiple-testing leads: 4
- Analyst neutral-gate passes: 2
- Analyst year-coverage passes: 0
- Analyst research leads: 0
- Latest report date: 2024-06-30
- Next action: `wait_for_report_rc_quota_reset_then_cache_next_analyst_month`

Blockers:

- `provider_quota_preflight_blocked`
- `full_factor_batch_readiness_blocked`
- `analyst_year_coverage_below_gate`
- `analyst_research_lead_count_zero`

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_non_lpr_orthogonal_source_gate.py tests\unit\test_cn_stock_non_lpr_orthogonal_source_gate_cli.py
```

Result: `6 passed`.

## Decision

The non-LPR source selector now defaults to the latest readiness evidence after LPR source closure. This keeps subsequent default runs aligned with the current source queue: analyst-report revision is selected but blocked, LPR remains closed to same-path retry, and no full factor batch is allowed.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
