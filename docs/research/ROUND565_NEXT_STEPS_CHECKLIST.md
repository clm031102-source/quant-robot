# Round565 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`.

## Current State

- New branch has been created from clean `main`.
- Startup context, Quant PM startup gate, CN stock startup gate, and CN stock data manifest have been run.
- Data manifest is `review_required` with known warnings and no blockers.
- HK-hold low-frequency state candidate plan is preregistered.
- Candidate-plan gate is `research_ready` with 3 active candidates and 9 / 9 controls complete.
- External-feed available-date join-smoke passed for all 3 HK-hold sponsorship seeds:
  - joined rows: 5,983,389 total;
  - signal dates: 547;
  - unique symbols per seed: 3,865;
  - available-date violations: 0;
  - same-day/future raw-date violations: 0.

## Recommended Next Work

1. Build the low-frequency state construction smoke for the 63-day state change, 126-day persistence, and local-liquidity interaction.
2. Keep the interaction liquidity leg local to price-volume data; do not substitute aggregate HSGT flow or old northbound-flow regimes.
3. Add reference dedup inputs against price-volume, moneyflow, and style exposures before residual IC.
4. Only after construction and dedup preparation pass, run a research-only residual IC prescreen with multiple-testing accounting.

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
