# CN Stock Round721 Paper Profile Optimizer Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round721 connected the paper-profile optimizer to the startup, data-manifest, and combined factor-batch readiness gates for CN processed-bars frontier candidates.

`scripts/run_paper_profile_optimizer.py` can tune paper risk profiles from frontier candidates. If readiness is blocked, it must not convert that state into a failed optimizer pack or any paper-profile artifact.

This was readiness-gate hardening only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward validation, promotion gates, signal generation, paper simulation from a ready packet, paper-profile optimization from a ready packet, or final-holdout reads.

## Change

Updated:

- `scripts/run_paper_profile_optimizer.py`
- `tests/unit/test_paper_profile_optimizer_cli.py`

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

- The constrained search pack is read and frontier candidates are selected first, but the output directory is not created yet.
- If any frontier candidate targets `CN` or `ALL`, startup gate, CN stock data manifest, and combined factor-batch readiness gate are validated before any profile simulation or output write.
- If readiness is blocked, `run_simulation` is not called and no optimizer output is written.
- The same gate paths are passed through to `run_simulation` for each profile attempt.
- Fixture and CN ETF-only processed-bars behavior is unchanged.

## Real CLI Smoke

Smoke used temporary no-BOM JSON files outside the repository:

- Frontier candidate: `CN_total_mv_log_top1_cost5_reb1`
- Source root: `data/processed`
- Startup gate: `data/reports/round707_factor_mining_startup_gate_20260709/factor_mining_startup_gate.json`
- Data manifest: `data/reports/round713_cn_stock_data_manifest_20260709/cn_stock_data_manifest.json`
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`
- Output dir: `data\reports\round721_paper_profile_optimizer_readiness_guard_smoke_20260709`

Expected blocked result:

- Exit code: non-zero.
- Error: `CN paper profile optimizer factor batch readiness gate is not ready`.
- Output directory `data\reports\round721_paper_profile_optimizer_readiness_guard_smoke_20260709` was not created.

## Verification

Red test first failed because a blocked CN readiness packet did not stop the optimizer before output/simulation.

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_paper_profile_optimizer_cli.py -q
```

Result: `5 passed`.

## Decision

Future CN processed-bars paper-profile optimizer runs must provide ready startup, data-manifest, and combined factor-batch readiness packets. The current Round708 readiness packet is blocked, so no CN paper-profile optimizer evidence should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
