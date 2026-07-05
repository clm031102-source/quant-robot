# Round564 Next Steps Checklist

Use this from latest `main`.

## Current State

- `main` contains Round555-Round563 work.
- Remote topic branch `codex/factor-batch-cn-stock-round555-20260705` has been deleted.
- Local topic branch has been deleted.
- Remote heads contain `origin/main` only.
- Daily-basic valuation repair is closed as diagnostic-only.

## Recommended Next Work

1. Pull latest `main`.
2. Create a new topic branch for the next factor batch.
3. Run the startup context, Quant PM startup gate, CN stock startup gate, and CN stock data manifest before factor generation.
4. Preregister a new PIT-safe orthogonal source family.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Daily-basic valuation repair parameter widening.
- Portfolio-grid promotion from raw shape or raw IC.
- Final-holdout tuning.
- Committing generated data or provider artifacts.
