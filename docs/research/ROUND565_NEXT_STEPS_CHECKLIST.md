# Round565 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`.

## Current State

- New branch has been created from clean `main`.
- Startup context, Quant PM startup gate, CN stock startup gate, and CN stock data manifest have been run.
- Data manifest is `review_required` with known warnings and no blockers.
- HK-hold low-frequency state candidate plan is preregistered.
- Candidate-plan gate is `research_ready` with 3 active candidates and 9 / 9 controls complete.

## Recommended Next Work

1. Build or reuse a source-construction smoke for HK-hold low-frequency state features.
2. Confirm available-date alignment and no same-day/future raw-date violations.
3. Add reference dedup inputs against price-volume, moneyflow, and style exposures before residual IC.
4. Only after source construction passes, run a research-only residual IC prescreen with multiple-testing accounting.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Provider download.
- Portfolio grid.
- Promotion gate.
- Final-holdout tuning.
- Daily-basic valuation repair parameter widening.
- Old northbound accumulation or crowding/reversal reruns.
- Margin-credit reentry.
- Committing generated data or provider artifacts.
