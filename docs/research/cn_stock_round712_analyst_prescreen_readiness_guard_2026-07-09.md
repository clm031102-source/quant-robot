# CN Stock Round712 Analyst Prescreen Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round712 connected the analyst-report revision prescreen CLI to the combined factor-batch readiness validator. This prevents the analyst prescreen entrypoint from starting when the combined quota/source/candidate gate is stale, blocked, or live-boundary unsafe.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `scripts/run_analyst_report_revision_prescreen.py`
- `tests/unit/test_analyst_report_revision_prescreen.py`

New CLI option:

```powershell
--factor-batch-readiness-gate <path-to-factor_batch_readiness_gate.json>
```

Behavior:

- If omitted, the historical CLI behavior remains available for existing tests and offline fixtures.
- If provided, the packet is validated before loading stock-basic, report, or bar data.
- A blocked readiness packet stops the CLI with a clear error before any prescreen outputs are written.

## Real CLI Smoke

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round701_analyst_report_revision_cache_202406_20260709 --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round712_analyst_prescreen_readiness_guard_smoke_20260709 --factor-batch-readiness-gate data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json
```

Expected blocked result:

- Exit code: non-zero.
- Error: `Analyst report revision prescreen factor batch readiness gate is not ready`.
- No prescreen JSON output was written.

## Verification

Red test was first observed failing because the CLI did not recognize `--factor-batch-readiness-gate`. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_revision_prescreen.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py -q
```

Result: `12 passed`.

Full related gate-chain verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_revision_prescreen.py tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_analyst_report_quota_pack.py tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py tests\unit\test_factor_mining_candidate_plan_gate.py tests\unit\test_factor_mining_candidate_plan_gate_cli.py -q
```

Result: `63 passed`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall scripts\run_analyst_report_revision_prescreen.py src\quant_robot\ops\factor_batch_readiness_gate.py
```

Result: passed.

## Decision

Use `--factor-batch-readiness-gate` for any future analyst-report revision prescreen run. The current blocked Round708/Round710 readiness packets must stop prescreen execution until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
