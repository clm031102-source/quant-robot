# CN Stock Three-Round Review Rounds 91-93 - 2026-06-21

## Scope

This review is the required 3-round governance checkpoint after Rounds 91, 92, and 93.

Machine/task/branch:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha
- Not scope: CN ETF rotation, live trading, broker/account/order actions

## Round Summary

| Round | Direction | Result | Useful Evidence | Decision |
|---:|---|---|---|---|
| 91 | Long-history `fina_indicator` backfill plan | planning-only two-symbol long-cycle request pack built | 2 symbols, 44 quarters, 88 requests, 5 batches, 0 blockers | planner accepted; no factor |
| 92 | Limited-symbol live `fina_indicator` backfill smoke | real long-history smoke passed after exact duplicate-row deduplication | 88 requests, 79 deduped rows, 9 empty requests, duplicate rows 0, PIT-ready datasets 100/100 | data path accepted; no factor |
| 93 | Broad-universe symbol shard plan | deterministic current-symbol shard plan built without Tushare calls | 5,208 included symbols, 321 BJ excluded, 44 periods, 229,152 planned requests, 53 shards | use first-10-symbol shard smoke before full shard |

## Promotion Count

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research leads carried forward after Round93: financial profitability-quality data capability only, not factor candidates
- New factor candidates from Rounds 91-93: 0

## Bright Data

The strongest useful evidence in this block is infrastructure evidence, not alpha evidence.

| Area | Evidence | Meaning |
|---|---|---|
| PIT availability | Round92 processed rows preserve `ann_date` and `end_date` across 2015-2025 report periods | true financial factors can later use announcement-date availability instead of future report-period data |
| Duplicate control | exact duplicate financial rows dropped processed rows from 144 to 79 and reduced duplicate rows from 65 to 0 | prevents duplicated statement rows from creating phantom factor strength |
| Resume safety | rerun skipped all 88 completed raw partitions, including recorded zero-row partitions | long backfills can resume without redownloading completed requests |
| Empty-response handling | 9 empty requests recorded instead of aborting the full smoke | sparse or unavailable report-period responses can be audited rather than hidden |
| PIT readiness | 100/100 financial-like datasets passed readiness in the Round92 smoke | the local shape is usable for later PIT factor construction |
| Backfill scale | current non-BJ universe implies 229,152 symbol-period requests split into 53 shards | the project now has a realistic cost/rate-limit plan before spending a large Tushare budget |

## Main Failure Pattern

Rounds 91-93 did not produce a bad factor; they deliberately avoided producing a premature factor.

The failure pattern being prevented is:

1. calling daily-basic valuation/liquidity proxies "profitability";
2. using report-period financial values before announcement dates;
3. running a huge full-universe financial backfill without budget, resume, duplicate, and PIT gates;
4. pre-registering ROE/ROA/margin factors from a two-symbol smoke sample;
5. interpreting data-pipeline readiness as alpha evidence.

## Direction Adjustment

Stop:

- profitability factor pre-registration from the two-symbol smoke;
- full-universe `fina_indicator` backfill before runtime and quality evidence;
- full 100-symbol shard execution before first-10-symbol shard smoke;
- any factor claim before PIT financial coverage exists at a usable breadth.

Continue:

- first-10-symbol shard backfill smoke from shard 1;
- `empty_response_policy="record"`;
- exact duplicate-row deduplication;
- PIT readiness after every financial-data backfill step;
- use `ann_date` as the information availability date for future financial factors;
- only after broader PIT coverage exists, pre-register profitability-quality factors such as ROE stability, margin improvement, profit growth, cash-flow quality, and accruals.

## Next Round

Round94 should be:

`round94_tushare_fina_indicator_first10_symbol_shard_backfill_smoke`

Expected request budget:

```text
10 symbols * 44 quarterly periods = 440 requests
```

Required after Round94:

- report runtime and empty-response rate;
- duplicate rows must remain 0 after processed rebuild;
- PIT readiness must pass;
- do not pre-register profitability factors if coverage or duplicate quality fails;
- do not launch a full 100-symbol shard until the first-10-symbol shard smoke is clean.

Budget stop-loss:

If Round94 shows high empty-response rate, duplicate drift, PIT readiness failure, or unacceptable runtime, do not expand the backfill. Fix the data path first, then repeat the small shard smoke.
