# CN Stock Round184-186 Three-Round Review

Date: 2026-06-23

## Scope

This review covers three completed rounds:

- Round184: add HK hold and LPR coverage audit, then execute 2025-01 external-feed shard.
- Round185: execute 2024-12 external-feed shard.
- Round186: execute 2024-11 external-feed shard.

These rounds are data-readiness and process-control work. They produced no promotable profitability factor and no IC or portfolio evidence.

## Results

Matrix-ready external-feed seeds after Round186:

| Seed | Observation dates | Joined rows | Unique symbols | Status |
| --- | ---: | ---: | ---: | --- |
| `margin_balance_crowding_reversal_20` | 271 | 1148598 | 4646 | history-ready, not alpha evidence |
| `margin_financing_acceleration_exhaustion_20` | 271 | 1148598 | 4646 | history-ready, not alpha evidence |
| `shibor_liquidity_tightening_regime_20` | 263 | 263 | n/a | history-ready regime-control seed |
| `index_location_value_liquidity_regime_20` | 286 | 286 | n/a | history-ready regime-control seed |

Blocked external-feed seeds:

| Seed or feed | Round186 state | Decision |
| --- | --- | --- |
| `northbound_hold_ratio_accumulation_20` | HK hold primary feed has 5 observation dates, 17204 rows, 3950 symbols, 91.5-day median gap | keep blocked |
| `northbound_hold_accumulation_flow_regime_20` | secondary `north_money` has 263 observation dates, but HK hold primary feed still has 5 observation dates | keep blocked |
| LPR-dependent policy factors | 263 macro rows, 263 complete SHIBOR rows, 0 LPR rows | keep blocked |

## Audit

What improved:

- Added a reusable coverage audit that blocks HK hold daily rank and LPR factors before IC or portfolio work.
- Extended margin-detail, HSGT flow, index-state, and SHIBOR coverage back to 2024-11.
- Kept available-date and raw-date checks clean: 0 PIT violations in join smoke.
- Prevented a false positive in Round186: raw HK hold progress rows looked continuous, but canonical CN-stock output was empty for that shard.

What did not improve enough:

- HK hold remains sparse in the canonical processed feed and cannot support daily cross-sectional stock ranking.
- LPR remains 0 non-null rows and cannot support policy-rate factors.
- Join smoke still is not alpha evidence; it only proves matrix readiness.

## Direction Adjustment

Continue external-feed backfill, but only for data-readiness:

- Next round: `round187_external_feed_202410_continue_margin_shibor_index_backfill_hk_hold_lpr_blocked`.
- Allowed seed families: margin-detail credit-cycle proxies, SHIBOR liquidity regime control, index-location regime control.
- Blocked seed families: HK hold daily ranking, LPR-dependent policy-rate factors.

Before any profitability claim:

- Run IC, quantile monotonicity, turnover decay, redundancy, regime coverage, cost/capacity walk-forward, and final-holdout gates.
- Treat 2026 as final holdout and do not tune after reading it.
- Do not count matrix-ready seeds as profitable factors.

## Conclusion

Round184-186 did not find a profitable factor. They did improve the process by preventing bad external feeds from entering factor mining and by extending the long-cycle matrix for four usable seed families. The right next action is controlled 2024-10 backfill, not HK hold/LPR parameter mining.
