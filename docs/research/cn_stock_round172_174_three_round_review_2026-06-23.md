# CN Stock Round172-174 Three-Round Review

Date: 2026-06-23

Scope: External macro, northbound, margin, index-state, and macro-rate data feed path for CN stock factor mining.

## Rounds Reviewed

- Round172: Built the long-cycle monthly shard plan for 2015-01-01 through 2025-12-31.
- Round173: Executed the 2025-12 shard with progress JSONL and reran join smoke.
- Round174: Executed the 2025-11 shard with progress JSONL and reran cumulative join smoke.

## What Worked

- The opaque Q4 backfill problem was fixed at the workflow level: each shard now writes per-endpoint progress events.
- Two monthly shards completed without process hangs or stderr errors.
- The common processed root can accumulate monthly shards while preserving per-shard reports.
- All join smoke runs had 0 `available_date` violations and 0 raw same-day/future date violations.
- Two margin seeds became history-ready after two months:
  - `margin_balance_crowding_reversal_20`
  - `margin_financing_acceleration_exhaustion_20`

## What Still Blocks Profitability Work

- This is still coverage and matrix-readiness evidence, not IC, RankIC, return, Sharpe, or win-rate evidence.
- Two months of data is too short for promotion and too short for robust external-feed mining.
- Index-state and SHIBOR seeds still need 60 observation dates; current coverage is 42-43.
- HK hold coverage is not yet suitable for northbound holding factors: after CN-stock filtering, only 2025-12-31 is retained across two shards.
- LPR remains missing or cached empty, so LPR-dependent liquidity/regime factors must stay blocked.

## Direction Audit

The direction is correct for this branch because the user assigned this office desktop to CN stock factor mining. It is not ETF rotation work and should not be evaluated as ETF rotation.

The work is not yet alpha mining in the strict sense. It is the required data and PIT infrastructure to avoid blind external-feed factor tests. Continuing one or two more monthly shards is higher value than running a two-month IC screen.

## Adjustment

Continue external-feed monthly backfill until at least the 60-observation seeds are history-ready. The next shard should be 2025-10. After that:

- If index-state and SHIBOR seeds become history-ready, run a matrix-readiness report only.
- Do not run portfolio grids until long-cycle coverage is much broader.
- Diagnose HK hold endpoint semantics before spending more rounds on northbound holding factors.
- Keep LPR-dependent seeds blocked until non-missing LPR coverage is available.

## Next Direction

Round175: execute the 2025-10 monthly shard with progress JSONL, rerun cumulative join smoke, and decide whether external-feed backfill can continue in a controlled batch or needs an HK hold/LPR coverage repair branch.
