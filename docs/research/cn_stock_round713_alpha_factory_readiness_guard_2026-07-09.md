# CN Stock Round713 Alpha Factory Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round713 connected the processed CN `tushare_alpha_factory` entrypoint to the combined factor-batch readiness validator. This is the actual factor-matrix / candidate-leaderboard generation path for Tushare-backed CN factors, so blocked quota/source/candidate readiness now stops the factory before market data is loaded.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Change

Updated:

- `scripts/run_tushare_alpha_factory.py`
- `tests/unit/test_tushare_alpha_factory_cli.py`

New CLI option:

```powershell
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
```

Processed CN behavior:

- Startup gate, data manifest, and candidate-plan gate still run first.
- The combined factor-batch readiness gate is then required and must be `ready`.
- Deprecated bypass flag `--allow-missing-factor-batch-readiness-gate` raises instead of bypassing.
- The output manifest gate trace now includes `factor_batch_readiness_gate_packet` when the factory actually runs.

## Real CLI Smoke

Fresh supporting evidence generated under ignored `data/reports`:

- CN stock data manifest: `data\reports\round713_cn_stock_data_manifest_20260709`; status `review_required`; blockers `[]`; warnings `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars`.
- Daily-basic candidate-plan gate: `data\reports\round713_daily_basic_candidate_plan_gate_for_alpha_factory_smoke_20260709`; status `research_ready`; blockers `[]`.

Smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_alpha_factory.py --source processed-bars --data-root data\processed --market CN --factor-source tushare_daily_basic --factor-input-root data\processed\tushare_factor_inputs --output-dir data\reports\round713_alpha_factory_readiness_guard_smoke_20260709 --startup-gate-packet data\reports\round707_factor_mining_startup_gate_20260709\factor_mining_startup_gate.json --data-manifest-packet data\reports\round713_cn_stock_data_manifest_20260709\cn_stock_data_manifest.json --allow-review-required-data-manifest --candidate-plan-gate-packet data\reports\round713_daily_basic_candidate_plan_gate_for_alpha_factory_smoke_20260709\factor_mining_candidate_plan_gate.json --factor-batch-readiness-gate-packet data\reports\round708_factor_batch_readiness_quota_preflight_20260709\factor_batch_readiness_gate.json
```

Expected blocked result:

- Exit code: non-zero.
- Error: `CN processed-bars alpha factory factor batch readiness gate is not ready`.
- Output directory `data\reports\round713_alpha_factory_readiness_guard_smoke_20260709` was not created.

## Verification

Red tests first failed because `run_alpha_factory_cli` did not accept `factor_batch_readiness_gate_packet`. After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_tushare_alpha_factory_cli.py tests\unit\test_factor_batch_readiness_gate.py tests\unit\test_factor_batch_readiness_gate_cli.py tests\unit\test_factor_mining_candidate_plan_gate.py tests\unit\test_factor_mining_candidate_plan_gate_cli.py tests\unit\test_cn_stock_data_manifest.py tests\unit\test_cn_stock_data_manifest_cli.py -q
```

Result: `48 passed`.

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall scripts\run_tushare_alpha_factory.py src\quant_robot\ops\factor_batch_readiness_gate.py
```

Result: passed.

## Decision

Any future processed CN alpha factory run must provide a ready combined factor-batch readiness packet. The current Round708 readiness packet is blocked, so the factory must not generate a fresh factor leaderboard until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
