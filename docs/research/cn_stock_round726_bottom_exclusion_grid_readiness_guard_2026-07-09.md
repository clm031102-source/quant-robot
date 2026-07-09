# CN Stock Round726 Bottom-Exclusion Grid Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round726 connected the shared bottom-exclusion grid loader to explicit startup, data-manifest, and combined factor-batch readiness packets before CN `processed-bars` or `authority-processed-bars` data can be loaded.

This protects the bottom-exclusion portfolio grid path and the wrappers that reuse it:

- `scripts/run_bottom_exclusion_portfolio_backtest.py`
- `scripts/run_bottom_exclusion_walk_forward.py`
- `scripts/run_beta_hedged_spread_audit.py`
- `scripts/run_benchmark_beta_exposure_audit.py`
- `scripts/run_dynamic_cash_overlay_backtest.py`

This was readiness hardening only. It did not download provider data, generate new factor formulas, run IC screens, run a ready portfolio grid, run walk-forward validation from a ready packet, run promotion gates, generate ready signals, run paper simulations, connect to brokers, read accounts, place orders, or read final holdout.

## Change

Added bottom-exclusion grid validation before bars are loaded:

```powershell
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

Behavior:

- CN `processed-bars` and `authority-processed-bars` grid runs now validate startup gate, CN data manifest, and combined factor-batch readiness gate before loading bars.
- Fixture-source and direct factor/label/bar-file runs are unchanged.
- The wrappers that call the shared bottom-exclusion grid loader can pass explicit readiness packet paths.
- CLI validation failures now exit with the gate error message instead of a Python traceback.

## Red Test

Added a focused test that builds a temporary CN grid config, cleared startup packet, cleared data manifest, and blocked factor-batch readiness packet.

Expected behavior:

- `run_bottom_exclusion_portfolio_backtest_cli(..., source="authority-processed-bars")` raises `factor batch readiness gate is not ready`.
- `load_authority_processed_bars_from_config` is not called.

The red test first failed because `run_bottom_exclusion_portfolio_backtest_cli` did not accept `startup_gate_packet`.

## Real CLI Smoke

Smoke used temporary no-BOM JSON files outside the repository:

- Grid market: `CN`.
- Source: `authority-processed-bars`.
- Startup gate: `data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json`.
- Data manifest: temporary cleared manifest matching the temporary data root.
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`.

Expected blocked result:

- CLI exit code: `1`.
- Error: `CN bottom-exclusion grid factor batch readiness gate is not ready`.
- Smoke output directory was not created.
- No Python traceback was emitted.

## Verification

Startup gates:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709 --market CN --asset-type stock --commits-allowed --confirm-start
```

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_bottom_exclusion_portfolio_backtest_cli tests.unit.test_bottom_exclusion_walk_forward tests.unit.test_beta_hedged_spread_audit tests.unit.test_benchmark_beta_exposure_audit tests.unit.test_dynamic_cash_overlay_backtest
```

Result: `13 tests`, `OK`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\run_bottom_exclusion_portfolio_backtest.py scripts\run_bottom_exclusion_walk_forward.py scripts\run_beta_hedged_spread_audit.py scripts\run_benchmark_beta_exposure_audit.py scripts\run_dynamic_cash_overlay_backtest.py
```

Result: exit code `0`.

## Decision

Future CN bottom-exclusion portfolio, walk-forward, beta-hedged spread, benchmark-beta exposure, and dynamic-cash overlay grid runs must provide ready startup, data-manifest, and combined factor-batch readiness packets before authority or processed bars are loaded. The current Round708 readiness packet is blocked, so these paths must not generate CN bottom-exclusion grid evidence until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
