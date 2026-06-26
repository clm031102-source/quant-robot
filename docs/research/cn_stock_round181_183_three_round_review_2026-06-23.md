# CN Stock Round181-183 Three-Round Review

Date: 2026-06-23

Scope: External macro, northbound, margin, index-state, and macro-rate data feed path for CN stock factor mining.

## Rounds Reviewed

- Round181: Added 2025-04. Four external-feed seeds remained matrix-ready; HK hold canonical output was empty.
- Round182: Added 2025-03. HK hold canonical output returned rows and primary coverage improved from 3 to 4 observation dates.
- Round183: Added 2025-02. Four seeds remained matrix-ready; HK hold canonical output was empty again.

## What Improved

- The external-feed backfill now covers eleven monthly shards in one processed root.
- Latest cumulative join smoke still has:
  - 0 `available_date` violations
  - 0 raw same-day/future-date violations
  - 0 failed seeds
- Four of six external-feed seeds are matrix-ready:
  - `index_location_value_liquidity_regime_20`
  - `margin_balance_crowding_reversal_20`
  - `margin_financing_acceleration_exhaustion_20`
  - `shibor_liquidity_tightening_regime_20`
- Latest cumulative join smoke reached 2586963 joined rows.

## What Did Not Improve

- Northbound hold seeds are still not matrix-ready. HK hold primary coverage is only 4 observation dates after eleven shards.
- LPR coverage is still missing/cached empty.
- No IC, RankIC, quantile return, portfolio return, Sharpe, win-rate, drawdown, cost, capacity, redundancy, regime robustness, or holdout evidence has been produced from these external feeds.

## Direction Audit

The data-readiness direction remains useful, but the review changes how to proceed:

- Continuing monthly backfill is valid for margin, SHIBOR, and index-state coverage.
- Continuing to design northbound-hold daily ranking factors is not valid until HK hold frequency is repaired or intentionally redesigned as a low-frequency state variable.
- Continuing to design LPR-dependent factors is not valid until LPR availability is repaired or explicitly marked unavailable.

## Adjustment

Proceed with Round184 for the 2025-01 shard, but pair it with a coverage audit:

- Audit HK hold frequency and canonical CN filtering behavior before any northbound-hold IC screen or portfolio grid.
- Audit LPR availability and decide whether to remove LPR from the active seed list or add a repair path.
- Keep external-feed portfolio grids blocked until long-cycle coverage, regime coverage, redundancy, cost/capacity, and statistical controls are available.

Blocked paths:

- No external-feed portfolio grid from eleven months of data.
- No profitability claim from matrix-ready seeds.
- No daily northbound-hold ranking factor until primary feed frequency is sufficient.
- No LPR factor while LPR remains missing.
