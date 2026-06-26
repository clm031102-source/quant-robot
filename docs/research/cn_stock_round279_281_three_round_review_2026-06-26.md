# CN Stock Round279-281 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock factor mining
- Review cadence: every 3 factor-mining rounds
- Covered rounds: 279, 280, 281
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Round Summary

| Round | Direction | Work | Result | Factor outcome |
|---:|---|---|---|---|
| 279 | financial reporting timeliness backfill with stock-basic filter | Completed shard 11 offset 10 and 15 | 10 fetched symbols, 1,242 active endpoint requests, 78 pre-listing requests skipped, 414 processed rows; aggregate coverage 267 symbols | 0 factors |
| 280 | continued statement backfill with stock-basic filter | Completed shard 12 offset 0 and 5 | 10 fetched symbols, 1,320 active endpoint requests, 443 processed rows; aggregate coverage 277 symbols | 0 factors |
| 281 | completed shard 12 with stock-basic filter | Completed shard 12 offset 10 and 15 | 10 fetched symbols, 1,290 active endpoint requests, 30 pre-listing requests skipped, 430 processed rows; aggregate coverage 284 symbols | 0 factors |

## Useful Output

The useful output remains data foundation and process improvement, not alpha:

- shard 11 is complete;
- shard 12 is complete;
- aggregate source coverage rose from 257 after Round278 to 284 after Round281;
- live Tushare ordinary statement backfill remains operational under throttling;
- all six Round279-281 subsegments passed required PIT statement readiness;
- stock-basic pre-listing filtering saved 108 endpoint requests across the three rounds;
- true post-filter empty endpoint requests were 0 across all three rounds;
- the Round279 combined quality report bug was fixed and regression-tested;
- the startup gate continues to block short-sample factor generation before the 1,000-symbol source gate.

## Coverage Progress

| Checkpoint | Aggregate unique symbols | Incremental coverage | Candidate plan allowed |
|---|---:|---:|---|
| after Round278 | 257 | - | false |
| after Round279 | 267 | +10 | false |
| after Round280 | 277 | +10 | false |
| after Round281 | 284 | +7 | false |

Coverage increased by 27 unique symbols over three rounds. This is steady progress, but the source gate is still far away: 284 is only 28.4% of the 1,000-symbol minimum.

Round281 also shows why fetched-symbol count is not enough. The round fetched 10 symbols, but 3 were already present in an older filtered PIT source, so net aggregate coverage increased by only 7.

## Quality Trend

| Round | Active Endpoint Requests | Pre-Listing Requests Skipped | Empty Requests | Duplicate Rows | Interpretation |
|---:|---:|---:|---:|---:|---|
| 279 | 1,242 | 78 | 0 | 0 | stock-basic filter fixed the Round278 pre-listing empty cluster |
| 280 | 1,320 | 0 | 0 | 3 | no empty waste, duplicate watch remains active |
| 281 | 1,290 | 30 | 0 | 0 | clean backfill, but net coverage overlap found |

The stock-basic filter is now confirmed as useful but not sufficient. It prevents wasting endpoint requests on pre-listing periods; it does not prevent spending endpoint budget on symbols already counted in the aggregate source union.

## Why No Factor Was Produced

No candidate factor was generated because the source gate did not clear.

The current aggregate state is:

| Metric | Value |
|---|---:|
| Aggregate rows | 61,139 |
| Aggregate unique symbols | 284 |
| Required unique symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

The blocker remains `unique_symbol_count_below_minimum`.

This remains the correct discipline. Creating factors from 284 symbols would convert a source-construction task into another short-sample overfitting run.

## Direction Audit

The financial reporting timeliness route is still not disproven. It remains a source-construction route that has not reached alpha-testing conditions.

Do not interpret Rounds 279-281 as:

- financial reporting timeliness alpha failed;
- accounting-quality alpha failed;
- announcement-delay factors failed.

The honest interpretation is:

- the data path works;
- coverage is increasing;
- PIT field readiness is intact;
- pre-listing request waste is now controlled;
- aggregate-overlap waste is now visible;
- the sample is still too small to mine alpha responsibly.

## Decision

Continue the financial reporting timeliness backfill route for Round282, but add a net-new source coverage preview before live endpoint requests.

Round282 must:

- continue with the mandatory stock-basic pre-listing filter;
- preview whether the next symbol segment is already present in the aggregate financial source union;
- report expected net-new symbols before running the Tushare backfill;
- continue blocking candidate generation until the 1,000-symbol source gate clears.

The preview was already run for the first Round282 segment and found 5 / 5 expected net-new symbols:

```text
002181.SZ, 000597.SZ, 000635.SZ, 002337.SZ, 000703.SZ
```

Rotate or pause if any of these occurs:

- aggregate unique-symbol coverage stops increasing across two consecutive subsegments;
- true post-listing empty-request rates recur after the list-date filter;
- required PIT fields fail;
- duplicate rows become material;
- Tushare throttling cost becomes unacceptable;
- coverage reaches 1,000 symbols and the first PIT prescreen produces zero credible residual leads.

## Next Direction

Round282 should continue from:

```text
shard_id=13, symbol_offset=0, symbol_limit=5
```

The command must include:

```text
--stock-basic-path data\processed\cn_stock_metadata\metadata\tushare_stock_basic
```

Expected next segment:

```text
002181.SZ, 000597.SZ, 000635.SZ, 002337.SZ, 000703.SZ
```

Blocked shortcuts for Round282:

- no financial reporting timeliness candidate generation before source gate;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no ignoring aggregate symbol overlap after Round281.

## Review Conclusion

Rounds 279-281 produced 0 new factors, 0 research leads, 0 paper-ready signals, and 0 promotable factors.

They did produce useful coverage progress and process hardening: aggregate source coverage increased to 284 symbols, shard 11 and shard 12 are complete, pre-listing request waste stayed controlled, and the next efficiency improvement is now clear. The correct next action is to continue source coverage from shard 13 offset 0 while adding a pre-run aggregate-overlap preview and blocking factor generation until the 1,000-symbol source gate clears.
