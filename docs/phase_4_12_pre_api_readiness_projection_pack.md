# Phase 4.12 Pre-API Readiness Projection Pack

Phase 4.12 consolidates current readiness evidence with local rehearsal projections.

It remains research-only. It does not modify real evidence, install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Projection builder in `quant_robot.ops.readiness_projection`.
- CLI artifact generation through `scripts/run_readiness_projection.py`.
- Core-check integration after `pre_api_readiness_board` and before `blocker_worklist`.
- One projection table for current versus projected readiness items.
- Delta and residual blocker tables for rehearsal tracks.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_readiness_projection.py --output-dir data\reports\readiness_projection
```

Output files:

- `readiness_projection_pack.json`
- `readiness_projection_pack.md`
- `readiness_projection_items.csv`
- `readiness_projection_deltas.csv`
- `readiness_projection_residuals.csv`

## Interpretation

This pack is a projection, not a real readiness-state change. It applies only explicit rehearsal projections:

- `data_gap_resolution` from the data-gap rehearsal.
- `provider_remediation` from the provider-remediation rehearsal.

All other readiness tracks keep their current board state. Use the delta and residual CSVs to see which local review rehearsals reduce blockers and which classes still remain before any API-boundary planning.
