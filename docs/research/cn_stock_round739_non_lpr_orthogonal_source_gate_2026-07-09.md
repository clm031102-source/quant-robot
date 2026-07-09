# CN Stock Round739 Non-LPR Orthogonal Source Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round739 consumed the Round738 LPR rejection-rotation gate, the Round729 factor-batch/local-prescreen readiness gate, and the Round729 analyst-report revision local prescreen.

This round selected the next non-LPR orthogonal source path but did not run a provider download, new factor batch, portfolio grid, promotion gate, paper signal, broker connection, account read, order placement, or final-holdout tuning.

## Implemented Gate

New files:

- `src/quant_robot/ops/cn_stock_non_lpr_orthogonal_source_gate.py`
- `scripts/run_cn_stock_non_lpr_orthogonal_source_gate.py`
- `tests/unit/test_cn_stock_non_lpr_orthogonal_source_gate.py`
- `tests/unit/test_cn_stock_non_lpr_orthogonal_source_gate_cli.py`

The gate:

- requires Round738 to have cleared rotation to a non-LPR source gate;
- keeps the failed LPR `gap_widening` residual path closed;
- reads the Round729 factor-batch readiness packet and separates local cached prescreen permission from full factor-batch readiness;
- reads the Round729 analyst-report local prescreen summary;
- selects `analyst_report_revision` as the current non-LPR PIT source path;
- blocks execution while provider quota, full factor-batch readiness, year coverage, and research-lead evidence remain insufficient;
- keeps portfolio grids, promotion, paper signals, final holdout, and live boundaries closed.

## Startup Gates

Quant PM startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709
```

Result: `status=ready`, `primary_market=CN_ETF`, blockers `[]`.

Factor-mining startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709 --market CN --asset-type stock --commits-allowed --confirm-start
```

Result: `status=cleared`, startup blockers `[]`, pushes disabled.

## Real Gate Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_non_lpr_orthogonal_source_gate.py --allow-blocked
```

Output: `data/reports/round739_non_lpr_orthogonal_source_gate_20260709`

Summary:

- Status: `blocked`
- Selected source: `analyst_report_revision`
- Source gate selected: true
- Source gate ready: false
- Local cached prescreen allowed: true
- Full factor batch allowed: false
- Provider request allowed: false
- Analyst candidate count: 4
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

Source rows:

| Source | Status | Local prescreen | Full batch | Research leads | Year passes | Next action |
|---|---|---|---|---:|---:|---|
| `analyst_report_revision` | selected but blocked by quota and year coverage | true | false | 0 | 0 | wait for quota reset, then cache next analyst month |
| `lpr_gap_widening_residual` | closed by Round738 rejection | false | false | 0 | 0 | do not rerun without a new LPR macro-interaction source gate |
| `local_no_provider_closed_queue` | closed or hibernated by Round703/Round704 queue evidence | false | false | 0 | 0 | no no-provider factor batch from closed local queue |

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_non_lpr_orthogonal_source_gate.py tests\unit\test_cn_stock_non_lpr_orthogonal_source_gate_cli.py
```

Result: `5 passed`.

## Decision

The next non-LPR orthogonal source is `analyst_report_revision`, but it is not ready for a fresh factor batch. Local cached prescreen permission remains useful for governance and replay only; it is not permission to run full factor mining, portfolio grids, promotion, paper signals, or live workflows.

The next useful action is quota-aware source extension: wait for `report_rc` quota reset, cache the next analyst-report month, then rerun the same frozen local prescreen. If quota remains unavailable, continue source governance or select a genuinely new PIT-safe source with its own gate.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
