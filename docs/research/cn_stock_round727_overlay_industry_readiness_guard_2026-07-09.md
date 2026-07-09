# CN Stock Round727 Overlay And Industry Readiness Guard

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round727 connected additional CN authority/processed-bars grid entrypoints to explicit startup, data-manifest, and combined factor-batch readiness gates before bars can be loaded.

Updated guarded entrypoints:

- `scripts/run_bottom_exclusion_overlay_audit.py`
- `scripts/run_industry_breadth_bridge_audit.py`
- `scripts/run_industry_neutral_ic_audit.py`
- `scripts/run_industry_neutral_portfolio_backtest.py`

This was readiness hardening plus one compatibility repair for the industry-neutral portfolio path. It did not download provider data, generate new factor formulas, run IC screens from a ready packet, run a ready overlay audit, run a ready industry audit, run promotion gates, generate ready signals, run paper simulations, connect to brokers, read accounts, place orders, or read final holdout.

## Change

Added readiness arguments:

```powershell
--startup-gate-packet <path-to-factor_mining_startup_gate.json>
--data-manifest-packet <path-to-cn_stock_data_manifest.json>
--factor-batch-readiness-gate-packet <path-to-factor_batch_readiness_gate.json>
--allow-review-required-data-manifest
```

Behavior:

- CN `processed-bars` and `authority-processed-bars` grid runs now validate startup gate, CN data manifest, and combined factor-batch readiness gate before loading bars.
- Direct factor/label-file runs remain unchanged.
- CLI validation failures now exit with the gate error message instead of a Python traceback.
- `run_industry_neutral_portfolio_backtest.py` now imports successfully against the current codebase.

## Compatibility Repair

The industry-neutral portfolio script referenced stale APIs:

- `prepare_research_pipeline_inputs`
- `research_input_fingerprint`
- `_pipeline_config` from `quant_robot.experiments.runner`

Those APIs are not available in the current codebase. Round727:

- Added `selection_method` back to `ResearchPipelineConfig`.
- Passes `selection_method` through to `run_factor_backtest`.
- Replaced the stale prepared-input cache path with the current public `run_research_pipeline(..., precomputed_factors=...)` path.
- Builds the required `ResearchPipelineConfig` locally inside the industry-neutral portfolio script.

## Red Tests

Added focused tests:

- Bottom-exclusion overlay grid with a blocked factor-batch readiness packet must not call `load_authority_processed_bars_from_config`.
- `ResearchPipelineConfig(selection_method="industry_neutral_top_n")` must pass that selection method to the backtest engine and record it in the request.

Initial failures:

- Overlay CLI did not accept `startup_gate_packet`.
- `ResearchPipelineConfig` did not accept `selection_method`.

## Real CLI Smokes

Smoke inputs used temporary no-BOM JSON files outside the repository.

Bottom-exclusion overlay audit:

- Grid market: `CN`.
- Source: `authority-processed-bars`.
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`.
- Exit code: `1`.
- Error: `CN bottom-exclusion overlay audit factor batch readiness gate is not ready`.
- Output directory was not created.
- No Python traceback was emitted.

Industry-neutral portfolio backtest:

- Grid market: `CN`.
- Source: `authority-processed-bars`.
- Readiness gate: `data/reports/round708_factor_batch_readiness_quota_preflight_20260709/factor_batch_readiness_gate.json`.
- Exit code: `1`.
- Error: `CN industry-neutral portfolio backtest factor batch readiness gate is not ready`.
- Output directory was not created.
- No Python traceback was emitted.

## Verification

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_bottom_exclusion_overlay_audit_cli tests.unit.test_bottom_exclusion_overlay_audit tests.unit.test_industry_neutral_ic_audit tests.unit.test_industry_breadth_bridge_audit
.\.venv\Scripts\python.exe -m unittest tests.unit.test_research_pipeline.ResearchPipelineTests.test_pipeline_passes_selection_method_to_backtest_engine
```

Import and compile checks:

```powershell
.\.venv\Scripts\python.exe -c "import scripts.run_industry_neutral_portfolio_backtest; print('import_ok')"
.\.venv\Scripts\python.exe -m py_compile scripts\run_bottom_exclusion_overlay_audit.py scripts\run_industry_breadth_bridge_audit.py scripts\run_industry_neutral_ic_audit.py scripts\run_industry_neutral_portfolio_backtest.py src\quant_robot\research\pipeline.py
```

## Decision

Future CN bottom-exclusion overlay, industry-breadth bridge, industry-neutral IC, and industry-neutral portfolio grid runs must provide ready startup, data-manifest, and combined factor-batch readiness packets before authority or processed bars are loaded. The current Round708 readiness packet is blocked, so these paths must not generate CN overlay or industry-grid evidence until quota/source/candidate readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
