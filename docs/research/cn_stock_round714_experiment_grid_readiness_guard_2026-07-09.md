# CN Stock Round714 Experiment Grid Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round714 connected the processed CN experiment-grid entrypoint to the combined factor-batch readiness validator. Portfolio or parameter grids should not run while quota/source/candidate readiness is blocked, because grid results can otherwise make a weak or unavailable source look actionable.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `scripts/run_experiment_grid.py`
- `tests/unit/test_experiment_grid_cli.py`

New CLI option:

```powershell
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
```

Processed CN behavior:

- Startup gate and data manifest still run first.
- The combined factor-batch readiness gate is then required and must be `ready`.
- Deprecated bypass flag `--allow-missing-factor-batch-readiness-gate` raises instead of bypassing.
- If readiness is blocked, bars are not loaded and no grid output is written.

## Real CLI Smoke

Smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\run_experiment_grid.py --config configs\experiment_grid.json --source processed-bars --data-root data\processed --output-dir data\reports\round714_experiment_grid_readiness_guard_smoke_20260709 --startup-gate-packet data\reports\round707_factor_mining_startup_gate_20260709\factor_mining_startup_gate.json --data-manifest-packet data\reports\round713_cn_stock_data_manifest_20260709\cn_stock_data_manifest.json --allow-review-required-data-manifest --factor-batch-readiness-gate-packet data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json
```

Expected blocked result:

- Exit code: non-zero.
- Error: `CN processed-bars experiment grid factor batch readiness gate is not ready`.
- Output directory `data\reports\round714_experiment_grid_readiness_guard_smoke_20260709` was not created.

## Verification

Red tests first failed because `run_grid` did not accept `factor_batch_readiness_gate_packet`. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_experiment_grid_cli.py tests\unit\test_tushare_alpha_factory_cli.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py tests\unit\test_cn_stock_data_manifest.py tests\unit\test_cn_stock_data_manifest_cli.py -q
```

Result: `38 passed`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall scripts\run_experiment_grid.py scripts\run_tushare_alpha_factory.py src\quant_robot\ops\factor_batch_readiness_gate.py
```

Result: passed.

## Decision

Any future processed CN experiment grid must provide a ready combined factor-batch readiness packet. The current Round708 readiness packet is blocked, so no portfolio/parameter grid should run until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
