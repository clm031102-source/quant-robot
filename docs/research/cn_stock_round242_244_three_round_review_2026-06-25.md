# CN Stock Round242-244 Three Round Review

Date: 2026-06-25
Machine: office_desktop
Scope: CN stock factor validation

## Rounds Reviewed

Round242: `docs/research/cn_stock_round242_accounting_quality_shard7_expansion_and_125_symbol_replay_2026-06-25.md`

Round243: `docs/research/cn_stock_round243_accounting_quality_shard7_offset5_data_prep_and_new_substructure_seed_2026-06-25.md`

Round244: `docs/research/cn_stock_round244_accounting_quality_new_substructure_implementation_and_prescreen_2026-06-25.md`

## What Changed

Round242 ended the old raw/repaired cash-accrual path. Across 115, 120, and 125 symbol replays, the raw and repaired candidates produced zero research leads.

Round243 expanded PIT statement readiness from 125 to 130 symbols and created a new-substructure seed instead of replaying the same failed formulas.

Round244 implemented two new formulas and added a dedicated `factor_mode=new_substructure` IC path so new hypotheses can be screened without mixing old cash-accrual candidates into the conclusion.

## Scorecard

| Round | Main action | New tested factors | Research leads | Promotable |
| --- | --- | ---: | ---: | ---: |
| 242 | 125-symbol replay of old raw/repaired family | 0 new, old family replay | 0 | 0 |
| 243 | 130-symbol readiness plus new seed | 0 | 0 | 0 |
| 244 | Implemented and screened new substructure factors | 2 | 0 | 0 |

## Bright Spots

- PIT data readiness improved to 130 symbols with zero matrix-label alignment violations.
- Formula registry now supports 7 formulas instead of 5.
- The residual IC tool now has a `new_substructure` mode, preventing accidental old-family reruns.
- `aq_abnormal_accrual_change_reversal` produced a 5-day raw IC of -0.0505 with t-stat -2.292 and p-value 0.0219.

The last point is only a directional audit clue. It failed FDR, ICIR, positive-rate, quantile spread, and neutral gates, so it is not a usable factor.

## Problems Found

The accounting-quality line is still data-light. Even with 130 symbols, the new-substructure prescreen had only 33-34 IC observations per factor-horizon pair. That is enough for a shape check, not enough for deployment confidence.

The first two new formulas are still close to the cash/accrual neighborhood. They are more orthogonal than the stopped raw formulas, but not far enough to create a strong new edge.

The best-looking signal is negative, which means the economic direction may be wrong or the result may be noise. Flipping it immediately would be multiple-testing leakage.

The balance-sheet stress relief idea shows weak industry-only improvement but does not survive size/liquidity neutralization.

## Audit Decision

No factor from Rounds242-244 should move to walk-forward, portfolio grid, paper trading, or live use.

Round245 should not spend another full round blindly expanding these two formulas. The only justified continuation is a preregistered directional audit of the abnormal accrual change sign. If that does not survive FDR and neutral gates, rotate to a more event-like accounting family:

- post-statement announcement drift
- profitability revision surprise
- muted reaction after statement improvement

## Required Adjustment

Before the next IC run:

- Count any sign inversion as a new hypothesis test.
- Keep `factor_mode=new_substructure` for new accounting-quality IC screens.
- Do not include old raw/repaired cash-accrual factors in the Round245 conclusion.
- Do not run portfolio grids until a factor passes FDR, neutral gates, and then walk-forward/cost/capacity/regime checks.
- Preserve final holdout.

This three-round block improved the process but did not find a tradable edge.
