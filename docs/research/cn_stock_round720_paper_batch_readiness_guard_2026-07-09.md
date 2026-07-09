# CN Stock Round720 Paper Batch Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round720 connected the paper-batch orchestration layer to the startup, data-manifest, and combined factor-batch readiness gates for CN processed-bars batches.

`scripts/run_paper_batch.py` can turn candidate leaderboards into many paper-simulation artifacts. It must not turn a blocked source/candidate/quota state into a batch summary full of failed candidate rows, because that still creates downstream evidence that can be mistaken for a completed paper batch.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward validation, promotion gates, signal generation, paper simulation from a ready packet, or final-holdout reads.

## Change

Updated:

- `scripts/run_paper_batch.py`
- `tests/unit/test_paper_batch_cli.py`

New config fields:

```json
{
  "startup_gate_packet": "data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json",
  "data_manifest_packet": "data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json",
  "factor_batch_readiness_gate_packet": "data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json",
  "allow_review_required_data_manifest": false
}
```

CN `processed-bars` behavior:

- Candidate rows are read first, but the output directory is not prepared yet.
- If any row targets `CN` or `ALL`, startup gate, CN stock data manifest, and combined factor-batch readiness gate are validated before output cleanup or candidate simulation.
- If readiness is blocked, `run_simulation` is not called and no paper-batch output is written.
- The same gate paths are passed through to `run_simulation` for each candidate profile.
- Fixture and non-CN processed-bars behavior is unchanged.

## Real CLI Smoke

Smoke used a temporary JSON config outside the repository with:

- Candidate leaderboard: `data/reports/cn_stock_daily_basic_factory_discovery_20260617_top20_cost10/candidate_leaderboard.csv`
- Source root: `data/processed`
- Startup gate: `data/reports/round707_factor_mining_startup_gate_20260709/factor_mining_startup_gate.json`
- Data manifest: `data/reports/round713_cn_stock_data_manifest_20260709/cn_stock_data_manifest.json`
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`
- Output dir: `data\reports\round720_paper_batch_readiness_guard_smoke_20260709`

Expected blocked result:

- Exit code: non-zero.
- Error: `CN paper batch factor batch readiness gate is not ready`.
- Output directory `data\reports\round720_paper_batch_readiness_guard_smoke_20260709` was not created.

## Verification

Red tests:

- First failed because `startup_gate_packet` was not passed to `run_simulation`.
- Second failed because a blocked readiness gate still allowed the batch to enter candidate simulation/output handling.

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_paper_batch_cli.py -q
```

Result: `11 passed`.

## Decision

Future CN processed-bars paper batches must provide ready startup, data-manifest, and combined factor-batch readiness packets. The current Round708 readiness packet is blocked, so no CN paper-batch evidence should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
