# CN Stock Round270-272 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Scope: CN A-share stock factor mining
- Review cadence: every 3 factor-mining rounds
- Covered rounds: 270, 271, 272
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Round Summary

| Round | Direction | Work | Result | Factor outcome |
|---:|---|---|---|---|
| 270 | financial reporting timeliness source audit | Audited local PIT financial reporting sources before candidate generation | 3 sources, 8,926 rows, max 100 symbols; blocked by source coverage | 0 factors |
| 271 | financial statement backfill viability | Repaired Tushare mappings/adapters, added request throttling, fixed aggregate source audit, completed shard 7 offset 10 and 15 | 10 fetched symbols, 1,320 endpoint requests, 440 processed rows; aggregate coverage 195 symbols | 0 factors |
| 272 | continued statement backfill | Completed shard 8 offset 0 and 5, reran aggregate audit | 10 fetched symbols, 1,320 endpoint requests, 465 processed rows; aggregate coverage 203 symbols | 0 factors |

## Useful Output

The useful output is not alpha yet. It is better research infrastructure:

- the project now blocks financial reporting timeliness factors before source coverage is broad enough;
- live Tushare ordinary statement backfill is rate-limit-safe enough to run in controlled subshards;
- aggregate source audit now measures union coverage across many shard roots instead of only the largest individual source;
- long-cycle coverage is viable: aggregate end-year coverage is 11 years through 2025;
- required PIT fields are present for the completed statement segments.

## Why No Factor Was Produced

No candidate factor was generated in Rounds 270-272 because the source gate did not clear.

The current aggregate coverage is:

| Metric | Value |
|---|---:|
| Aggregate rows | 41,494 |
| Aggregate unique symbols | 203 |
| Required unique symbols | 1,000 |
| End-year count | 11 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

The blocker is only `unique_symbol_count_below_minimum`.

This is a productive failure mode. It prevents the project from making the same earlier mistake: extracting an attractive IC or return curve from too-small samples and treating it as a tradable profitability factor.

## Direction Audit

The financial reporting timeliness direction is not yet disproven. It has not reached the stage where alpha can be fairly tested.

Do not interpret this as:

- financial reporting timeliness alpha failed;
- accounting-quality alpha failed;
- announcement-delay factors failed.

The honest interpretation is narrower:

- the data pipeline works;
- the field and year coverage look viable;
- cross-sectional coverage remains too small for mining.

## Stop-Loss And Rotation Rule

Continue this family only while the backfill is making clean coverage progress without repeated endpoint failures or data-quality failures.

Rotate away if any of these happens:

- source coverage stops increasing despite more subshards;
- empty-request or missing-field rates become material;
- Tushare rate limits make the wall-clock cost unacceptable;
- coverage reaches 1,000 symbols and the first PIT prescreen produces zero credible residual leads.

Do not rotate merely because no factor exists yet. The current work is source construction, not formula search.

## Next Direction

Round273 should continue the backfill from:

```text
shard_id=8, symbol_offset=10, symbol_limit=5
```

Blocked shortcuts for Round273:

- no same-family factor generation before source gate;
- no short-sample IC screen;
- no portfolio grid;
- no promotion or paper-ready claim;
- no final holdout access.

## Review Conclusion

Rounds 270-272 produced 0 new factors, 0 research leads, 0 paper-ready signals, and 0 promotable factors.

They did produce a useful and safer research path: a verified financial-statement backfill channel with aggregate coverage accounting. The next correct action is to continue increasing source coverage or rotate only if the backfill path stops being cost-effective.

