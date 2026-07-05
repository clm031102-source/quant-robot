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
- Reference-dedup prep is complete without using returns or IC:
  - persistence max abs same-day Spearman overlap: 0.5662 vs `liquidity_rank` / `log_adv20_amount`;
  - state-change max abs overlap: 0.2305 vs `volatility_20`;
  - liquidity-interaction max abs overlap: 0.2760 vs `liquidity_rank`;
  - no reference reached 0.70 on any date.
- Research-only residual IC prescreen completed for all 3 candidates:
  - research leads: 0 / 3;
  - all candidates rejected after effect-size and multiple-testing gates;
  - max exit date: 2025-12-31;
  - 2026 final holdout was not read.
- Closeout package records the rejection and blocks tuning, sign flips, parameter widening, portfolio grids, promotion gates, and final-holdout reads for this family.

## Recommended Next Work

1. Merge this branch back to `main` after final validation.
2. Delete the topic branch after `main` is pushed and verified.
3. Start Round566 from latest `main` on a new topic branch.
4. Rotate to a genuinely new PIT-safe source mechanism only after preregistration and candidate-plan gate.

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
