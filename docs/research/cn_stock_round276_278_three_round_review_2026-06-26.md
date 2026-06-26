# CN Stock Round276-278 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock factor mining
- Review cadence: every 3 factor-mining rounds
- Covered rounds: 276, 277, 278
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Round Summary

| Round | Direction | Work | Result | Factor outcome |
|---:|---|---|---|---|
| 276 | financial reporting timeliness backfill | Completed shard 10 offset 0 and 5 | 10 fetched symbols, 1,320 endpoint requests, 440 processed rows; aggregate coverage 240 symbols | 0 factors |
| 277 | continued statement backfill | Completed shard 10 offset 10 and 15 | 10 fetched symbols, 1,320 endpoint requests, 436 processed rows; aggregate coverage 249 symbols | 0 factors |
| 278 | continued statement backfill with endpoint watch | Completed shard 11 offset 0 and 5 | 10 fetched symbols, 1,320 endpoint requests, 423 processed rows; aggregate coverage 257 symbols | 0 factors |

## Useful Output

The useful output remains data foundation and process improvement, not alpha:

- shard 10 is complete;
- shard 11 is half complete;
- aggregate source coverage rose from 231 after Round275 to 257 after Round278;
- live Tushare ordinary statement backfill remains operational under throttling;
- all six Round276-278 subsegments passed required PIT statement readiness;
- empty-request root cause analysis identified a stock-basic list-date filtering gap;
- the backfill CLI now has a reusable `--stock-basic-path` pre-listing filter;
- the startup gate continues to block short-sample factor generation before the 1,000-symbol source gate.

## Coverage Progress

| Checkpoint | Aggregate unique symbols | Incremental coverage | Candidate plan allowed |
|---|---:|---:|---|
| after Round275 | 231 | - | false |
| after Round276 | 240 | +9 | false |
| after Round277 | 249 | +9 | false |
| after Round278 | 257 | +8 | false |

Coverage increased by 26 unique symbols over three rounds. This is steady progress, but the source gate is still far away: 257 is only 25.7% of the 1,000-symbol minimum.

## Quality Trend

| Round | Empty Requests | Duplicate Rows | Interpretation |
|---:|---:|---:|---|
| 276 | 0 | 0 | clean backfill segment |
| 277 | 17 | 1 | endpoint watch remained active |
| 278 | 53 | 0 | spike traced to `300997.SZ` pre-listing statement periods |

The Round278 empty-request spike changed the process plan. It does not prove that the factor family is weak; it proves that blindly requesting all 2015-2025 periods for every symbol wastes endpoint budget when symbols listed later.

## Why No Factor Was Produced

No candidate factor was generated because the source gate did not clear.

The current aggregate state is:

| Metric | Value |
|---|---:|
| Aggregate rows | 54,667 |
| Aggregate unique symbols | 257 |
| Required unique symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

The blocker remains `unique_symbol_count_below_minimum`.

This remains the correct discipline. Creating factors from 257 symbols would convert a data-construction task into another short-sample overfitting run.

## Direction Audit

The financial reporting timeliness route is still not disproven. It remains a source-construction route that has not reached alpha-testing conditions.

Do not interpret Rounds 276-278 as:

- financial reporting timeliness alpha failed;
- accounting-quality alpha failed;
- announcement-delay factors failed.

The honest interpretation is:

- the data path works;
- coverage is increasing;
- PIT field readiness is intact;
- request planning was inefficient for later-listed stocks;
- the sample is still too small to mine alpha responsibly.

## Decision

Continue the financial reporting timeliness backfill route for Round279, but with a mandatory stock-basic pre-listing filter.

Rotate or pause if any of these occurs:

- aggregate unique-symbol coverage stops increasing across two consecutive subsegments;
- true post-listing empty-request rates remain high after the list-date filter;
- required PIT fields fail;
- duplicate rows become material;
- Tushare throttling cost becomes unacceptable;
- coverage reaches 1,000 symbols and the first PIT prescreen produces zero credible residual leads.

## Next Direction

Round279 should continue from:

```text
shard_id=11, symbol_offset=10, symbol_limit=5
```

The command must include:

```text
--stock-basic-path data\processed\cn_stock_metadata\metadata\tushare_stock_basic
```

Expected next segment:

```text
002012.SZ, 000721.SZ, 002132.SZ, 001213.SZ, 000603.SZ
```

Blocked shortcuts for Round279:

- no financial reporting timeliness candidate generation before source gate;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access;
- no ignoring pre-listing request waste after the Round278 `300997.SZ` cluster.

## Review Conclusion

Rounds 276-278 produced 0 new factors, 0 research leads, 0 paper-ready signals, and 0 promotable factors.

They did produce useful coverage progress and a concrete engineering improvement: aggregate source coverage increased to 257 symbols, shard 10 completed, shard 11 reached half completion, and the backfill process now has a reusable stock-basic list-date filter. The correct next action is to continue source coverage from shard 11 offset 10 while blocking factor generation until the 1,000-symbol source gate clears.
