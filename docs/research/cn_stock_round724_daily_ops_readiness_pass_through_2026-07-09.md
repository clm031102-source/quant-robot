# CN Stock Round724 Daily Ops Readiness Pass-Through

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round724 connected Daily Ops to explicit startup, data-manifest, and combined factor-batch readiness packets when it generates a fresh signal snapshot or paper simulation.

`scripts/run_daily_ops.py` can either read existing signal/simulation artifacts or generate them by calling `run_signal_snapshot` and `run_simulation`. Those child entrypoints already enforce CN processed-bars readiness. The Daily Ops wrapper now exposes the same readiness packet arguments so a CN run can reproduce the exact evidence chain.

This was readiness pass-through only. It did not download provider data, generate new factor formulas, run IC screens, generate a ready signal snapshot, run a ready paper simulation, create advisory tickets from a ready packet, place orders, connect to brokers, read accounts, or read final holdout.

## Change

Updated:

- `scripts/run_daily_ops.py`
- `tests/unit/test_daily_ops_cli.py`

New arguments:

```powershell
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

Behavior:

- When Daily Ops generates a signal snapshot, it passes the configured readiness packets to `run_signal_snapshot`.
- When Daily Ops generates a paper simulation, it passes the configured readiness packets to `run_simulation`.
- Existing artifact-read mode is unchanged.
- The CLI now reports validation failures as a clean `SystemExit` message instead of printing a Python traceback.

## Real CLI Smoke

Smoke used temporary no-BOM JSON files outside the repository:

- Promotion candidate: `CN_momentum_2_top1_reb1`
- Market: `CN`
- Factor: `momentum_2`
- Source: `processed-bars`
- Data root: `data/processed`
- Startup gate: `data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json`
- Data manifest: `data/reports/round713_cn_stock_data_manifest_20260709/cn_stock_data_manifest.json`
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`

Expected blocked result:

- Exit code: `1`.
- Error: `CN signal snapshot factor batch readiness gate is not ready`.
- Daily Ops output directory was not created.
- The retry after CLI cleanup emitted the readiness error without a Python traceback.

## Verification

Red test first failed because `run_daily_ops` did not accept `startup_gate_packet`.

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_daily_ops_cli.py -q
```

Result: `6 passed`.

## Decision

Future CN processed-bars Daily Ops runs that generate signal or paper-simulation artifacts must provide ready startup, data-manifest, and combined factor-batch readiness packets. The current Round708 readiness packet is blocked, so no CN Daily Ops signal/simulation evidence should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
