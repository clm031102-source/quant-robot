# CN Stock Round562 Daily-Basic Shape/Exposure Gate Trace

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: add gate-packet traceability to the daily-basic valuation shape/exposure diagnostic CLI and rerun the H1 2024 audit with explicit packet paths.

## Code Change

`scripts\run_daily_basic_valuation_shape_exposure_audit.py` now accepts:

- `--startup-gate-packet`
- `--data-manifest-packet`
- `--candidate-plan-gate-packet`

The CLI records these paths in:

- the returned result object;
- the printed CLI summary;
- `daily_basic_valuation_shape_exposure_audit.json`.

This mirrors the alpha-factory traceability pattern without changing the diagnostic's promotion policy.

## Test Evidence

- Added `tests\unit\test_daily_basic_valuation_shape_exposure_audit_cli.py`.
- Focused red test first failed because `startup_gate_packet` was not a supported CLI function argument.
- After implementation, focused CLI test passed.
- Existing daily-basic valuation shape/exposure audit tests plus the new CLI test passed: 4 tests.
- Python compile passed for the CLI and operation module.

## Real Diagnostic Smoke

Reran the H1 2024 diagnostic:

| Field | Value |
| --- | --- |
| Output | `data\reports\round562_daily_basic_valuation_shape_exposure_audit_h1_2024_gate_trace_20260705` |
| Start | 2024-01-02 |
| End | 2024-06-28 |
| Horizon | 20 |
| Execution lag | 1 |

Gate packets recorded:

| Packet | Path |
| --- | --- |
| Startup gate | `data\reports\factor_mining_startup_gate\factor_mining_startup_gate.json` |
| Data manifest | `data\reports\round555_cn_stock_data_manifest_combined_20260705\cn_stock_data_manifest.json` |
| Candidate-plan gate | `data\reports\round555_daily_basic_source_smoke_candidate_plan_gate_20260705\factor_mining_candidate_plan_gate.json` |

Summary:

| Metric | Value |
| --- | ---: |
| Overall passes | false |
| Shape pass count | 1 |
| Exposure passes | false |
| Residual candidate factors | 0 |

Blockers:

- `no_residual_candidate_after_lightweight_exposure_audit`
- `style_coverage_below_threshold`

## Decision

Keep daily-basic valuation repair diagnostic-only. The traceability improvement is complete, but the H1 audit still rejects the family after industry/style residualization.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download.
- No final-holdout tuning.
- Generated `data/reports` artifacts remain out of Git.
