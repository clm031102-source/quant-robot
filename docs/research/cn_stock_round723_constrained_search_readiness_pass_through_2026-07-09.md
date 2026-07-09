# CN Stock Round723 Constrained Search Readiness Pass-Through

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round723 added explicit readiness packet pass-through to the constrained candidate search pipeline when it needs to run a fresh walk-forward stage.

`scripts/run_constrained_candidate_search.py` is historically a CN ETF risk-constrained orchestration script, but it wraps `run_walk_forward`. If reused with a CN stock processed-bars config and fresh artifact generation, it must be able to carry the exact startup, data-manifest, and combined factor-batch readiness evidence into that walk-forward stage.

This was readiness pass-through only. It did not change the existing `reuse_existing_artifacts` semantics, did not download provider data, generate new factor formulas, run IC screens, run a ready walk-forward, run paper batches, run promotion gates, generate signals, run paper simulation, or read final holdout.

## Change

Updated:

- `scripts/run_constrained_candidate_search.py`
- `tests/unit/test_constrained_candidate_search_cli.py`

New config fields:

```json
{
  "startup_gate_packet": "data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json",
  "data_manifest_packet": "data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json",
  "factor_batch_readiness_gate_packet": "data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json",
  "allow_review_required_data_manifest": false
}
```

Behavior:

- When constrained search runs a fresh walk-forward stage, it passes the configured readiness packets to `run_walk_forward`.
- The constrained search output pack records the configured readiness packet paths in `config`.
- The CLI now reports validation failures as a clean `SystemExit` message instead of printing a Python traceback.
- Existing artifact reuse behavior is unchanged.

## Real CLI Smoke

Smoke used a temporary no-BOM JSON config outside the repository:

- Source: `processed-bars`
- Data root: `data/processed`
- Walk-forward config: `configs/walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704.json`
- Startup gate: `data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json`
- Data manifest: `data/reports/round713_cn_stock_data_manifest_20260709/cn_stock_data_manifest.json`
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`
- `reuse_existing_artifacts`: `false`

Expected blocked result:

- Exit code: `1`.
- Error: `CN walk-forward validation factor batch readiness gate is not ready`.
- Constrained search output directory was not created.
- Walk-forward output directory was not created.
- The retry after CLI cleanup emitted the readiness error without a Python traceback.

## Verification

Red tests first failed because `run_constrained_candidate_search` did not pass readiness packet fields to `run_walk_forward`, and the CLI leaked traceback output on validation failures.

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_constrained_candidate_search_cli.py -q
```

Result: `4 passed`.

## Decision

Future CN stock processed-bars constrained search configs that run a fresh walk-forward stage must provide ready startup, data-manifest, and combined factor-batch readiness packets. The current Round708 readiness packet is blocked, so no CN constrained-search walk-forward evidence should be generated until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
