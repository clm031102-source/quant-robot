# CN Stock Round175-177 Three-Round Review

Date: 2026-06-23

Scope: External macro, northbound, margin, index-state, and macro-rate data feed path for CN stock factor mining.

## Rounds Reviewed

- Round175: Added 2025-10, fixed transient empty trade-calendar retry, and made three seeds history-ready.
- Round176: Added 2025-09 and made SHIBOR history-ready.
- Round177: Added 2025-08 and confirmed the same four seeds remain history-ready.

## What Improved

- The external-feed backfill path is now observable and resilient to one transient empty `trade_cal` response.
- Five monthly shards are accumulated in one processed root with per-shard reports.
- All cumulative join smoke runs still have:
  - 0 `available_date` violations
  - 0 raw same-day/future date violations
  - 0 fail seeds
- Four of six external-feed seeds are matrix-ready:
  - `index_location_value_liquidity_regime_20`
  - `margin_balance_crowding_reversal_20`
  - `margin_financing_acceleration_exhaustion_20`
  - `shibor_liquidity_tightening_regime_20`

## What Did Not Improve

- Northbound hold seeds are still not matrix-ready. `external_hk_hold` only has 2 primary observation dates across five shards after CN-stock filtering.
- LPR coverage is still missing/cached empty, so LPR-dependent liquidity/regime features must remain blocked.
- No IC, RankIC, quantile return, portfolio return, Sharpe, win-rate, drawdown, cost, capacity, redundancy, or regime robustness evidence has been produced from these external feeds.

## Direction Audit

The direction remains correct: this is CN stock factor infrastructure, not ETF rotation. It addresses the earlier process flaw of blind short-window mining by expanding point-in-time external feed coverage before any profitability claim.

The work should not yet shift into factor promotion. The right next action is to continue controlled backfill and separately audit the frequency semantics of HK hold and LPR availability.

## Adjustment

Proceed with one of two safe paths:

- Primary path: Continue monthly backfill with 2025-07 to broaden history for the four ready seeds.
- Parallel/next audit path: Build an HK hold frequency/coverage audit and an LPR coverage repair probe before spending more rounds on northbound-hold or LPR-dependent seed families.

Blocked paths:

- Do not run external-feed portfolio grids from five recent months.
- Do not treat matrix-ready seeds as profitable factors.
- Do not treat HK hold as daily northbound holding data without a frequency audit.
- Do not use LPR factors until non-missing LPR coverage exists.

## Next Direction

Round178 should execute the 2025-07 monthly shard with progress JSONL, then rerun cumulative join smoke. If the same blockers persist after Round178, prioritize an HK hold/LPR coverage repair audit before further northbound/LPR factor design.
