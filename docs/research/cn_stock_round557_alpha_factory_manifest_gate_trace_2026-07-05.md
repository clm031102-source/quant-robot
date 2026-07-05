# CN Stock Round557 Alpha Factory Manifest Gate Trace

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: make CN processed-bars alpha-factory outputs audit-traceable by recording the startup, data-manifest, and candidate-plan gate packet paths in the returned result and `manifest.json`.

## Change

`scripts\run_tushare_alpha_factory.py` now attaches:

```json
"gate_packets": {
  "startup_gate_packet": "...",
  "data_manifest_packet": "...",
  "candidate_plan_gate_packet": "..."
}
```

for CN processed-bars runs.

If `manifest.json` already exists in the alpha-factory output directory, the same `gate_packets` object is written there. Fixture and non-CN paths are unchanged.

## Test-First Evidence

Red test:

- `test_processed_cn_alpha_factory_accepts_cleared_startup_gate_packet` first failed with `KeyError: 'gate_packets'`.

Green tests:

- The focused test now verifies both the returned result and `manifest.json` contain the three gate packet paths.
- `tests.unit.test_tushare_alpha_factory_cli` and `tests.unit.test_alpha_factory`: 20 tests passed.
- Python compile passed for `scripts\run_tushare_alpha_factory.py`.

## Decision

Future alpha-factory evidence should include both:

- Gate enforcement before bar loading.
- Gate packet traceability in the run manifest.

This still does not promote any candidate. It only makes later audit/review less brittle.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download.
- No generated `data/reports` artifact is committed.
