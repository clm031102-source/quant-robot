# CN Stock Round178-180 Three-Round Review

Date: 2026-06-23

Scope: External macro, northbound, margin, index-state, and macro-rate data feed path for CN stock factor mining.

## Rounds Reviewed

- Round178: Added 2025-07 and confirmed four external-feed seeds remained matrix-ready.
- Round179: Added 2025-06 and added one more HK hold primary observation date.
- Round180: Added 2025-05 and confirmed the same four seeds remained matrix-ready; formal HK hold canonical CN output was empty for this shard.

## What Improved

- The controlled monthly backfill now covers eight recent monthly shards in one processed root.
- All cumulative join smoke runs still have:
  - 0 `available_date` violations
  - 0 raw same-day/future date violations
  - 0 failed seeds
- Four of six external-feed seeds are matrix-ready:
  - `index_location_value_liquidity_regime_20`
  - `margin_balance_crowding_reversal_20`
  - `margin_financing_acceleration_exhaustion_20`
  - `shibor_liquidity_tightening_regime_20`
- Round180 cumulative join smoke reached 1890624 joined rows, with margin seeds covering 709115 joined rows and 4585 unique symbols.

## What Did Not Improve

- Northbound hold seeds are still not matrix-ready. `external_hk_hold` still has only 3 primary observation dates across the cumulative root.
- The Round180 shard produced zero canonical CN-stock `external_hk_hold` rows, so raw progress rows must not be interpreted as usable factor history.
- LPR coverage is still missing/cached empty, so LPR-dependent liquidity or policy-rate features remain blocked.
- No IC, RankIC, quantile return, portfolio return, Sharpe, win-rate, drawdown, cost, capacity, redundancy, or regime robustness evidence has been produced from these external feeds.

## Direction Audit

The direction remains correct, but the boundary is strict: this is still data-readiness and PIT join infrastructure, not alpha discovery.

This work directly addresses the earlier flaw of short-window blind factor mining by forcing long-cycle, source-specific, available-date-safe evidence before any portfolio grid. It also prevents a new mistake: treating matrix-ready external fields as profitable factors.

## Adjustment

Proceed with controlled monthly backfill, but keep two hard blockers active:

- Do not run portfolio grids from the external-feed seeds until the long-cycle coverage target and regime coverage gate are met.
- Do not test northbound-hold daily ranking factors until HK hold frequency and canonical CN coverage are repaired or redesigned as low-frequency state variables.

Next action:

- Round181 should execute the 2025-04 monthly shard with progress JSONL.
- After more coverage, run an HK hold frequency/coverage audit and an LPR availability repair probe before spending additional rounds on northbound-hold or LPR-dependent factor design.
