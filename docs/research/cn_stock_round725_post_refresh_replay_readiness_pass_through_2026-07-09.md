# CN Stock Round725 Post-Refresh Replay Readiness Pass-Through

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round725 connected post-refresh replay to explicit startup, data-manifest, and combined factor-batch readiness packets when it invokes Daily Ops after a recent data refresh.

`scripts/run_post_refresh_replay.py` is an upstream orchestration layer. If recent data is ready, it calls `run_daily_ops`, which may generate a fresh signal snapshot and paper simulation. Daily Ops now enforces readiness through its child entrypoints; post-refresh replay must be able to pass the same packet paths down.

This was readiness pass-through only. It did not download provider data, generate new factor formulas, run IC screens, generate a ready signal snapshot, run a ready paper simulation, create advisory tickets from a ready packet, place orders, connect to brokers, read accounts, or read final holdout.

## Change

Updated:

- `scripts/run_post_refresh_replay.py`
- `tests/unit/test_post_refresh_replay.py`

New arguments:

```powershell
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

Behavior:

- When recent data is ready and post-refresh replay invokes Daily Ops, the configured readiness packets are passed to `run_daily_ops`.
- Existing not-ready recent-refresh blocking behavior is unchanged.
- Existing downstream-error behavior is unchanged: downstream validation failures are recorded in the post-refresh replay pack as `replay_failed`.

## Real CLI Smoke

Smoke used temporary no-BOM JSON files outside the repository:

- Recent refresh pack: ready/completed.
- Recent refresh output dir: `data/processed`.
- Promotion candidate: `CN_momentum_2_top1_reb1`.
- Market: `CN`.
- Factor: `momentum_2`.
- Startup gate: `data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json`.
- Data manifest: `data/reports/round713_cn_stock_data_manifest_20260709/cn_stock_data_manifest.json`.
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`.

Expected blocked result:

- CLI exit code: `0`, because post-refresh replay records downstream failures as a report pack.
- Pack status: `replay_failed`.
- Blocker: `post_refresh_downstream_failed: CN signal snapshot factor batch readiness gate is not ready`.
- Post-refresh report directory was created.
- Daily Ops child output directory was not created.

## Verification

Red test first failed because `run_post_refresh_replay` did not accept `startup_gate_packet`.

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_post_refresh_replay.py -q
```

Result: `3 passed`.

## Decision

Future CN processed-bars post-refresh replay runs must provide ready startup, data-manifest, and combined factor-batch readiness packets before they can produce Daily Ops signal/simulation evidence. The current Round708 readiness packet is blocked, so post-refresh replay may only record downstream failure packs until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
