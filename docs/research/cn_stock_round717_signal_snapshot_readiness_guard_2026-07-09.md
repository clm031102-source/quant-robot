# CN Stock Round717 Signal Snapshot Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round717 connected the research-only signal snapshot CLI to the startup, data-manifest, and combined factor-batch readiness gates for CN processed-bars runs.

Signal snapshots and advisory rebalance plans can look actionable even when they are research-only. They must not be generated from CN processed bars while quota/source/candidate readiness is blocked.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward validation, promotion gates, signal generation from a ready packet, or final-holdout reads.

## Change

Updated:

- `scripts/run_signal_snapshot.py`
- `tests/unit/test_signal_snapshot_cli.py`

New CLI options:

```powershell
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

CN `processed-bars` behavior for `market=CN` and `market=ALL`:

- Startup gate is required and must be cleared.
- CN stock data manifest is required and must be cleared, unless review-required mode is explicitly allowed.
- Combined factor-batch readiness gate is required and must be `ready`.
- If readiness is blocked, bars are not loaded and no signal snapshot or rebalance-plan output is written.
- Fixture and CN ETF-only processed-bars behavior is unchanged.

## Real CLI Smoke

Smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\run_signal_snapshot.py --source processed-bars --data-root data\processed --market CN --factor momentum_2 --factor-windows 2 --top-n 1 --output-dir data\reports\round717_signal_snapshot_readiness_guard_smoke_20260709 --startup-gate-packet data\reports\round707_factor_mining_startup_gate_20260709\factor_mining_startup_gate.json --data-manifest-packet data\reports\round713_cn_stock_data_manifest_20260709\cn_stock_data_manifest.json --allow-review-required-data-manifest --factor-batch-readiness-gate-packet data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json
```

Expected blocked result:

- Exit code: non-zero.
- Error: `CN signal snapshot factor batch readiness gate is not ready`.
- Output directory `data\reports\round717_signal_snapshot_readiness_guard_smoke_20260709` was not created.

## Verification

Red tests first failed because `run_signal_snapshot` did not accept startup/readiness packet arguments. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_signal_snapshot_cli.py -q
```

Result: `4 passed`.

## Decision

Future CN processed-bars signal snapshots must provide ready startup, data-manifest, and combined factor-batch readiness packets. The current Round708 readiness packet is blocked, so no CN signal snapshot or advisory rebalance plan should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
