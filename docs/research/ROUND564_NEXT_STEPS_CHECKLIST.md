# Round564 Next Steps Checklist

Use this from latest `main`.

## Start Here

- Machine: `office_desktop`.
- Task: `factor_batch`.
- Suggested branch example: `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`.
- First safe check:

```powershell
python scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-round565-pit-source-plan-20260705
```

- Stop before factor generation unless startup context, Quant PM startup gate, CN stock startup gate, CN stock data manifest, and candidate-plan gate all clear or are explicitly reviewed when status is `review_required` with no blockers.
- Treat older commands in `CURRENT_RESEARCH_INDEX.md` as historical evidence unless the latest checklist repeats them.

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
