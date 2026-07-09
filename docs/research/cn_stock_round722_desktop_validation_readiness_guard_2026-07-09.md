# CN Stock Round722 Desktop Validation Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round722 connected the desktop residual-regime validation wrappers to explicit startup, data-manifest, and combined factor-batch readiness packets.

`scripts/run_desktop_factor_validation.py` and `scripts/run_waited_desktop_factor_validation.py` are orchestration entrypoints around `run_walk_forward`. They should not rely only on implicit default gate paths when a CN processed-bars validation run needs to reproduce the exact readiness evidence used by a batch.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids from a ready packet, walk-forward validation from a ready packet, promotion gates, signal generation, paper simulation, or final-holdout reads.

## Change

Updated:

- `scripts/run_desktop_factor_validation.py`
- `scripts/run_waited_desktop_factor_validation.py`
- `tests/unit/test_desktop_factor_validation.py`
- `tests/unit/test_waited_desktop_factor_validation.py`

New arguments:

```powershell
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

CN `processed-bars` behavior:

- Direct desktop validation now passes the explicit readiness packets through to `run_walk_forward`.
- The waited desktop validation queue now passes the same packets through to its runner.
- Default desktop validation still uses the standard readiness packet paths when explicit paths are not supplied.
- Waited validation CLI now reports validation failures as a clean `SystemExit` message instead of printing a Python traceback.
- Fixture behavior is unchanged.

## Startup Gates

Before the real CN processed-bars smoke checks, the required startup gates were rerun:

- Quant PM startup gate status: `ready`.
- CN stock factor-mining startup gate status: `cleared`.
- Machine/task/branch: `office_desktop` / `factor_batch` / `codex/factor-batch-cn-stock-source-readiness-round695-20260709`.
- Commits allowed: `true`.
- Pushes allowed: `false`.

## Real CLI Smoke

Direct desktop validation smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_desktop_factor_validation.py `
  --config configs\walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704.json `
  --source processed-bars `
  --data-root data\processed `
  --output-dir data\reports\round722_desktop_validation_readiness_guard_smoke_20260709 `
  --startup-gate-packet data\reports\factor_mining_startup_gate\factor_mining_startup_gate.json `
  --data-manifest-packet data\reports\round713_cn_stock_data_manifest_20260709\cn_stock_data_manifest.json `
  --allow-review-required-data-manifest `
  --factor-batch-readiness-gate-packet data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json
```

Expected blocked result:

- Exit code: `1`.
- Error: `CN walk-forward validation factor batch readiness gate is not ready`.
- Output directory `data\reports\round722_desktop_validation_readiness_guard_smoke_20260709` was not created.

Waited desktop validation smoke:

- Exit code: `1`.
- Error: `CN walk-forward validation factor batch readiness gate is not ready`.
- Summary JSON was not written.
- Validation output directory was not created.
- The retry after CLI cleanup emitted the readiness error without a Python traceback.

## Verification

Red tests first failed because both wrappers rejected `startup_gate_packet`.

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_desktop_factor_validation.py tests\unit\test_waited_desktop_factor_validation.py tests\unit\test_walk_forward_cli.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py tests\unit\test_cn_stock_data_manifest.py tests\unit\test_cn_stock_data_manifest_cli.py -q
```

Result: `34 passed`.

```powershell
.\.venv\Scripts\python.exe -m compileall scripts\run_desktop_factor_validation.py scripts\run_waited_desktop_factor_validation.py scripts\run_walk_forward.py src\quant_robot\ops\factor_batch_readiness_gate.py src\quant_robot\ops\cn_stock_data_manifest.py src\quant_robot\ops\factor_mining_startup.py
```

Result: exit code `0`.

`git diff --check` result: exit code `0`, with only CRLF normalization warnings for touched text files.

## Decision

Future CN processed-bars desktop validation and waited desktop validation runs must carry ready startup, data-manifest, and combined factor-batch readiness packets. The current Round708 readiness packet is blocked, so no CN desktop validation evidence should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
