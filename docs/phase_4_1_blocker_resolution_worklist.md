# Phase 4.1 Blocker Resolution Worklist

Phase 4.1 turns the pre-API readiness board into a local blocker-resolution worklist.

It remains research-only. It does not connect to providers, brokers, accounts, order systems, or live trading.

## What It Adds

- Worklist builder in `quant_robot.ops.blocker_worklist`.
- CLI artifact generation through `scripts/run_blocker_worklist.py`.
- Core-check integration after the pre-API readiness board.
- Open work items mapped from blocker IDs to local-only commands.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_blocker_worklist.py --output-dir data\reports\blocker_worklist
```

Output files:

- `blocker_resolution_worklist.json`
- `blocker_resolution_worklist.md`
- `blocker_work_items.csv`
- `blocker_action_queue.csv`

## Interpretation

The worklist converts each readiness-board blocker into an `open` local work item with:

- `work_item_id`;
- `track_id`;
- `blocker_id`;
- severity;
- evidence;
- primary local command;
- `local_only=true`.

The action queue deduplicates readiness-board commands while preserving priority order.

## Current Local State

The current worklist is expected to remain open because the project still has data-quality, provider-readiness, and manual-review blockers. This is useful progress: the local operational loop now ends with a concrete work queue instead of a raw blocker list.
