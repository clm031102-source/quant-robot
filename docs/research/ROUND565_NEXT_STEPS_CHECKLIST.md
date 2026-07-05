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
- Low-frequency construction smoke also passed without PIT violations:
  - joined rows: 1,241,443;
  - joined signal dates: 364;
  - joined symbols: 3,568;
  - max raw HK-hold date used: 2025-09-30;
  - 2025-12-31 raw rows used before 2026 availability: 0.

## Recommended Next Work

1. Add reference dedup inputs against price-volume, moneyflow, and style exposures before residual IC.
2. Keep the interaction liquidity leg local to price-volume data; do not substitute aggregate HSGT flow or old northbound-flow regimes.
3. Run a research-only residual IC prescreen only after dedup preparation is explicit and multiple-testing accounting is wired in.
4. Keep portfolio grids, promotion gates, and 2026 final-holdout reads blocked.

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
