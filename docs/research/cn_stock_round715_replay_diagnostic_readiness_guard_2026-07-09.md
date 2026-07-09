# CN Stock Round715 Replay And Diagnostic Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round715 connected two downstream CN validation entrypoints to the combined factor-batch readiness validator:

- `scripts/run_same_parameter_full_sample_replay.py`
- `scripts/run_extreme_trade_diagnostic.py`

These scripts can create replay or diagnostic evidence that looks actionable. They must not run from CN processed bars or authority-processed bars while quota/source/candidate readiness is blocked.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `scripts/run_same_parameter_full_sample_replay.py`
- `scripts/run_extreme_trade_diagnostic.py`
- `tests/unit/test_same_parameter_replay_cli.py`
- `tests/unit/test_extreme_trade_diagnostic_cli.py`

New CLI option on both scripts:

```powershell
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
```

CN behavior for `processed-bars` and `authority-processed-bars`:

- Startup gate and data manifest still run first.
- The combined factor-batch readiness gate is then required and must be `ready`.
- If readiness is blocked, bars are not loaded and no replay or diagnostic output is written.

## Real CLI Smokes

Same-parameter replay smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_same_parameter_full_sample_replay.py --candidates-csv data\reports\cn_stock_daily_basic_factory_discovery_20260617_top20_cost10\candidate_leaderboard.csv --base-config configs\experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621.json --source processed-bars --data-root data\processed --output-dir data\reports\round715_same_parameter_replay_readiness_guard_smoke_20260709 --startup-gate-packet data\reports\round707_factor_mining_startup_gate_20260709\factor_mining_startup_gate.json --data-manifest-packet data\reports\round713_cn_stock_data_manifest_20260709\cn_stock_data_manifest.json --allow-review-required-data-manifest --factor-batch-readiness-gate-packet data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json --max-candidates 1
```

Expected blocked result:

- Exit code: non-zero.
- Error: `CN same-parameter full-sample replay factor batch readiness gate is not ready`.
- Output directory `data\reports\round715_same_parameter_replay_readiness_guard_smoke_20260709` was not created.

Extreme-trade diagnostic smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_extreme_trade_diagnostic.py --config configs\experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621.json --factor-name value_low_turnover_low_tail_20 --source processed-bars --data-root data\processed --output-dir data\reports\round715_extreme_trade_diagnostic_readiness_guard_smoke_20260709 --startup-gate-packet data\reports\round707_factor_mining_startup_gate_20260709\factor_mining_startup_gate.json --data-manifest-packet data\reports\round713_cn_stock_data_manifest_20260709\cn_stock_data_manifest.json --allow-review-required-data-manifest --factor-batch-readiness-gate-packet data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json --diagnostic-top-n 1
```

Expected blocked result:

- Exit code: non-zero.
- Error: `CN extreme trade diagnostic factor batch readiness gate is not ready`.
- Output directory `data\reports\round715_extreme_trade_diagnostic_readiness_guard_smoke_20260709` was not created.

## Verification

Red tests first failed because both functions did not accept `factor_batch_readiness_gate_packet`. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_same_parameter_replay_cli.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_extreme_trade_diagnostic_cli.py -q
```

Results:

- Same-parameter replay CLI tests: `3 passed`.
- Extreme-trade diagnostic CLI tests: `2 passed`.

## Decision

Future CN same-parameter replay and extreme-trade diagnostic runs must provide a ready combined factor-batch readiness packet. The current Round708 readiness packet is blocked, so no replay or diagnostic evidence should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
