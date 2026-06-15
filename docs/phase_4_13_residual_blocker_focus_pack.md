# Phase 4.13 Residual Blocker Focus Pack

Phase 4.13 turns Phase 4.12 residual blockers into a prioritized local focus pack.

It remains research-only. It does not mutate real readiness evidence, install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.

## What It Adds

- Focus-pack builder in `quant_robot.ops.residual_blocker_focus`.
- CLI artifact generation through `scripts/run_residual_blocker_focus.py`.
- Core-check integration after `blocker_worklist`.
- A prioritized root-focus table for remaining residual blocker tracks.
- A downstream wait table showing manual-review blockers that are waiting on upstream cleanup.
- A compact action queue scoped to the focused blocker tracks.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_blocker_focus.py --output-dir data\reports\residual_blocker_focus
```

Output files:

- `residual_blocker_focus_pack.json`
- `residual_blocker_focus_pack.md`
- `residual_focus_items.csv`
- `residual_downstream_waits.csv`
- `residual_focus_actions.csv`

## Interpretation

This pack is a local planning artifact, not a real readiness-state change.

It uses the readiness projection residuals as root focus tracks:

- `data_gap_resolution` covers the remaining projected data-gap blockers and links related `data_quality` work items.
- `provider_remediation` covers the remaining projected provider-remediation blockers and links related `provider_readiness` work items.

The manual-review gate remains downstream until those upstream blocker classes are cleared and the live-boundary review lock is intentionally handled in a later phase.
