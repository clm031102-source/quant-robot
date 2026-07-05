# Round563 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705` or after it is merged into `main`.

## Current State

- Round554-Round562 work is packaged for safe sync.
- Daily-basic valuation repair remains rejected.
- Alpha-factory and daily-basic exposure diagnostics now carry gate packet traceability.
- Topic branch is ready for mainline integration after validation.

## Recommended Next Work

1. Merge `codex/factor-batch-cn-stock-round555-20260705` into `main` after validation.
2. Delete the remote topic branch after `main` is pushed and verified.
3. Start the next factor batch from latest `main` on a new topic branch.
4. Use a new preregistered PIT-safe source family; do not widen daily-basic valuation repair.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Daily-basic valuation repair parameter widening.
- Portfolio-grid promotion from raw shape or raw IC.
- Final-holdout tuning.
- Committing generated data or provider artifacts.
