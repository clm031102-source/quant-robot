# CN Stock Round716 Walk-Forward Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round716 connected the generic walk-forward validation CLI to the combined factor-batch readiness validator for CN processed-bars runs.

Walk-forward output is high-impact validation evidence. It must not be generated from CN processed bars while quota/source/candidate readiness is blocked.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward validation, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `scripts/run_walk_forward.py`
- `tests/unit/test_walk_forward_cli.py`

New CLI options:

```powershell
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

CN `processed-bars` behavior:

- Startup gate is required and must be cleared.
- CN stock data manifest is required and must be cleared, unless review-required mode is explicitly allowed.
- Combined factor-batch readiness gate is required and must be `ready`.
- If readiness is blocked, bars are not loaded and no walk-forward output is written.
- Fixture and non-CN processed-bars behavior is unchanged.

## Real CLI Smoke

Smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704.json --source processed-bars --data-root data\processed --output-dir data\reports\round716_walk_forward_readiness_guard_smoke_20260709 --startup-gate-packet data\reports\round707_factor_mining_startup_gate_20260709\factor_mining_startup_gate.json --data-manifest-packet data\reports\round713_cn_stock_data_manifest_20260709\cn_stock_data_manifest.json --allow-review-required-data-manifest --factor-batch-readiness-gate-packet data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json
```

Expected blocked result:

- Exit code: non-zero.
- Error: `CN walk-forward validation factor batch readiness gate is not ready`.
- Output directory `data\reports\round716_walk_forward_readiness_guard_smoke_20260709` was not created.

## Verification

Red test first failed because `run_walk_forward` did not accept startup/readiness packet arguments. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_walk_forward_cli.py -q
```

Result: `5 passed`.

## Decision

Future CN processed-bars walk-forward validation must provide ready startup, data-manifest, and combined factor-batch readiness packets. The current Round708 readiness packet is blocked, so no walk-forward validation evidence should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
