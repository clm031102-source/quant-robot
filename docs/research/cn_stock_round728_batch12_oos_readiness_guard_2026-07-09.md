# CN Stock Round728 Batch12 OOS Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round728 connected the locked Batch12 CN stock OOS validation CLI to explicit startup, data-manifest, and combined factor-batch readiness gates before authority bars or authority daily-basic inputs can be loaded.

Updated:

- `scripts/run_cn_stock_batch12_oos_validation.py`
- `tests/unit/test_cn_stock_batch12_oos_validation_cli.py`

This was readiness hardening only. It did not download provider data, generate new factor formulas, run a ready OOS validation, run promotion gates, generate ready signals, run paper simulations, connect to brokers, read accounts, place orders, or read final holdout.

## Change

Added a testable wrapper:

```python
run_cn_stock_batch12_oos_validation_from_files(...)
```

Added readiness arguments:

```powershell
--data-root <manifest-source-root>
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

Behavior:

- The CLI now validates startup gate, CN data manifest, and combined factor-batch readiness before loading authority bars or daily-basic inputs.
- Validation failures exit with the gate error message instead of a Python traceback.

## Red Test

Added a focused test that builds temporary handoff/preflight JSON, a cleared startup packet, a cleared data manifest, and a blocked factor-batch readiness packet.

Expected behavior:

- `run_cn_stock_batch12_oos_validation_from_files(...)` raises `factor batch readiness gate is not ready`.
- `load_authority_processed_bars_from_config` is not called.
- `load_authority_processed_dataset_from_config` is not called.

The red test first failed because the script did not expose `run_cn_stock_batch12_oos_validation_from_files`.

## Real CLI Smoke

Smoke used temporary no-BOM JSON files outside the repository:

- Handoff: temporary minimal JSON.
- Preflight: temporary minimal JSON.
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`.
- Exit code: `1`.
- Error: `CN batch12 OOS validation factor batch readiness gate is not ready`.
- Output directory was not created.
- No Python traceback was emitted.

## Verification

Focused test:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cn_stock_batch12_oos_validation_cli
```

Result: `1 test`, `OK`.

## Decision

Future Batch12 CN stock OOS validation runs must provide ready startup, data-manifest, and combined factor-batch readiness packets before authority bars or daily-basic inputs are loaded. The current Round708 readiness packet is blocked, so Batch12 OOS validation must not generate new evidence until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
