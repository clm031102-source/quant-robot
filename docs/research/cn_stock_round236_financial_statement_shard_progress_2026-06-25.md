# CN Stock Round236 Financial Statement Shard Progress - 2026-06-25

## Scope

Round236 continues the accounting-quality statement backfill before any factor preregistration.

This progress report covers executable shard tooling and completed subshards through shard 6 offset 10 limit 5. No factor was generated and no profitability claim was made.

## Tooling Added

Added a repeatable shard/subshard execution entrypoint:

```text
scripts/run_financial_statement_shard_backfill.py
```

It reads:

```text
data/reports/round236_financial_statement_symbol_shard_plan_20260625/financial_statement_symbol_shard_plan.json
```

Then it records:

- shard id;
- symbol offset and limit;
- selected symbols;
- endpoint request budget;
- processed rows;
- empty requests;
- required-column readiness result.

Unit coverage:

```text
tests/unit/test_financial_statement_shard_backfill_cli.py
```

## VIP Route Audit

The possible high-efficiency Tushare VIP route was checked first:

- `income_vip`: blocked, no permission;
- `balancesheet_vip`: blocked, no permission;
- `cashflow_vip`: blocked, no permission.

Decision: continue with ordinary per-symbol statement endpoints until the token permission level changes.

## Completed Subshards

| Segment | Symbols | Endpoint requests | Processed rows | Empty requests | Readiness |
|---|---:|---:|---:|---:|---|
| shard 1 offset 0 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 1 offset 2 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 1 offset 4 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 1 offset 6 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 1 offset 8 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 1 offset 10 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 1 offset 12 limit 2 | 2 | 264 | 88 | 2 | passed |
| shard 1 offset 14 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 1 offset 16 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 1 offset 18 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 2 offset 0 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 2 offset 2 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 2 offset 4 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 2 offset 6 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 2 offset 8 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 2 offset 10 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 2 offset 12 limit 2 | 2 | 264 | 88 | 2 | passed |
| shard 2 offset 14 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 2 offset 16 limit 2 | 2 | 264 | 88 | 4 | passed |
| shard 2 offset 18 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 3 offset 0 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 3 offset 2 limit 2 | 2 | 264 | 88 | 2 | passed |
| shard 3 offset 4 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 3 offset 6 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 3 offset 8 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 3 offset 10 limit 2 | 2 | 264 | 88 | 5 | passed |
| shard 3 offset 12 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 3 offset 14 limit 2 | 2 | 264 | 88 | 2 | passed |
| shard 3 offset 16 limit 2 | 2 | 264 | 88 | 3 | passed |
| shard 3 offset 18 limit 2 | 2 | 264 | 88 | 2 | passed |
| shard 4 offset 0 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 4 offset 2 limit 2 | 2 | 264 | 88 | 3 | passed |
| shard 4 offset 4 limit 2 | 2 | 264 | 89 | 0 | passed |
| shard 4 offset 6 limit 2 | 2 | 264 | 88 | 2 | passed |
| shard 4 offset 8 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 4 offset 10 limit 2 | 2 | 264 | 88 | 3 | passed |
| shard 4 offset 12 limit 2 | 2 | 264 | 73 | 54 | passed |
| shard 4 offset 14 limit 2 | 2 | 264 | 88 | 13 | passed |
| shard 4 offset 16 limit 2 | 2 | 264 | 88 | 7 | passed |
| shard 4 offset 18 limit 2 | 2 | 264 | 88 | 12 | passed |
| shard 5 offset 0 limit 2 | 2 | 264 | 88 | 11 | passed |
| shard 5 offset 2 limit 2 | 2 | 264 | 88 | 3 | passed |
| shard 5 offset 4 limit 2 | 2 | 264 | 88 | 4 | passed |
| shard 5 offset 6 limit 2 | 2 | 264 | 89 | 3 | passed |
| shard 5 offset 8 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 5 offset 10 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 5 offset 12 limit 2 | 2 | 264 | 88 | 1 | passed |
| shard 5 offset 14 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 5 offset 16 limit 2 | 2 | 264 | 88 | 2 | passed |
| shard 5 offset 18 limit 2 | 2 | 264 | 88 | 0 | passed |
| shard 6 offset 0 limit 5 | 5 | 660 | 220 | 0 | passed |
| shard 6 offset 5 limit 5 | 5 | 660 | 221 | 8 | passed |
| shard 6 offset 10 limit 5 | 5 | 660 | 220 | 18 | passed |
| total | 115 | 15,180 | 5,048 | 175 | passed |

Completed symbols:

- `000066.SZ`
- `300029.SZ`
- `000519.SZ`
- `000538.SZ`
- `002329.SZ`
- `000676.SZ`
- `000906.SZ`
- `000407.SZ`
- `601318.SH`
- `000020.SZ`
- `000002.SZ`
- `002357.SZ`
- `603223.SH`
- `000007.SZ`
- `000055.SZ`
- `000019.SZ`
- `000570.SZ`
- `000525.SZ`
- `000719.SZ`
- `000513.SZ`
- `000510.SZ`
- `000852.SZ`
- `000420.SZ`
- `000006.SZ`
- `000504.SZ`
- `000028.SZ`
- `002049.SZ`
- `000058.SZ`
- `000626.SZ`
- `000729.SZ`
- `600604.SH`
- `000859.SZ`
- `000532.SZ`
- `000910.SZ`
- `000016.SZ`
- `000629.SZ`
- `000528.SZ`
- `000607.SZ`
- `000032.SZ`
- `000665.SZ`
- `000011.SZ`
- `000652.SZ`
- `001696.SZ`
- `000526.SZ`
- `000507.SZ`
- `000558.SZ`
- `000524.SZ`
- `002094.SZ`
- `000655.SZ`
- `000017.SZ`
- `000089.SZ`
- `000410.SZ`
- `000530.SZ`
- `000592.SZ`
- `000565.SZ`
- `002211.SZ`
- `000601.SZ`
- `000598.SZ`
- `000401.SZ`
- `000520.SZ`
- `000550.SZ`
- `000757.SZ`
- `000030.SZ`
- `000798.SZ`
- `001872.SZ`
- `000027.SZ`
- `000723.SZ`
- `000552.SZ`
- `000708.SZ`
- `000544.SZ`
- `000012.SZ`
- `000518.SZ`
- `300959.SZ`
- `002121.SZ`
- `002024.SZ`
- `000009.SZ`
- `000568.SZ`
- `000501.SZ`
- `000637.SZ`
- `000968.SZ`
- `000554.SZ`
- `000795.SZ`
- `000713.SZ`
- `000099.SZ`
- `000869.SZ`
- `000850.SZ`
- `002021.SZ`
- `000025.SZ`
- `000697.SZ`
- `300008.SZ`
- `002047.SZ`
- `000686.SZ`
- `000759.SZ`
- `000548.SZ`
- `000004.SZ`
- `000848.SZ`
- `002209.SZ`
- `000008.SZ`
- `000547.SZ`
- `000488.SZ`
- `000428.SZ`
- `000778.SZ`
- `000557.SZ`
- `000426.SZ`
- `000630.SZ`
- `000612.SZ`
- `000001.SZ`
- `002162.SZ`
- `000505.SZ`
- `000702.SZ`
- `000506.SZ`
- `000938.SZ`
- `600608.SH`
- `000551.SZ`
- `000423.SZ`

Empty requests observed:

- `balancesheet:000066.SZ:20220331`
- `balancesheet:000519.SZ:20220331`
- `balancesheet:000906.SZ:20200630`
- `balancesheet:000002.SZ:20240930`
- `income:603223.SH:20150331`
- `balancesheet:603223.SH:20150331`
- `income:000570.SZ:20230930`
- `cashflow:000729.SZ:20160331`
- `income:000532.SZ:20150630`
- `cashflow:000532.SZ:20150630`
- `balancesheet:000528.SZ:20160331`
- `cashflow:000607.SZ:20160930`
- `income:000607.SZ:20180930`
- `income:000607.SZ:20181231`
- `income:000652.SZ:20150930`
- `balancesheet:000526.SZ:20160930`
- `cashflow:000526.SZ:20190630`
- `balancesheet:000655.SZ:20210331`
- `income:000410.SZ:20160331`
- `income:000089.SZ:20180930`
- `balancesheet:000089.SZ:20200331`
- `income:000410.SZ:20211231`
- `cashflow:000410.SZ:20251231`
- `balancesheet:002211.SZ:20170630`
- `cashflow:002211.SZ:20230930`
- `income:000601.SZ:20160630`
- `cashflow:000598.SZ:20221231`
- `balancesheet:000598.SZ:20250630`
- `income:000520.SZ:20170331`
- `cashflow:000520.SZ:20240930`
- `cashflow:000550.SZ:20150630`
- `income:000798.SZ:20191231`
- `balancesheet:000030.SZ:20221231`
- `balancesheet:000030.SZ:20231231`
- `income:000723.SZ:20160930`
- `cashflow:000723.SZ:20210331`
- `cashflow:000012.SZ:20160930`
- `income:000012.SZ:20210630`
- `balancesheet:000518.SZ:20230630`
- `income:300959.SZ:20150331`
- `balancesheet:300959.SZ:20150331`
- `cashflow:300959.SZ:20150331`
- `income:300959.SZ:20150630`
- `balancesheet:300959.SZ:20150630`
- `cashflow:300959.SZ:20150630`
- `income:300959.SZ:20150930`
- `balancesheet:300959.SZ:20150930`
- `cashflow:300959.SZ:20150930`
- `cashflow:300959.SZ:20151231`
- `income:300959.SZ:20160331`
- `balancesheet:300959.SZ:20160331`
- `cashflow:300959.SZ:20160331`
- `income:300959.SZ:20160630`
- `balancesheet:300959.SZ:20160630`
- `cashflow:300959.SZ:20160630`
- `cashflow:300959.SZ:20160930`
- `income:300959.SZ:20161231`
- `balancesheet:300959.SZ:20161231`
- `cashflow:300959.SZ:20161231`
- `income:300959.SZ:20170331`
- `balancesheet:300959.SZ:20170331`
- `cashflow:300959.SZ:20170331`
- `income:002121.SZ:20170331`
- `income:300959.SZ:20170630`
- `balancesheet:300959.SZ:20170630`
- `cashflow:300959.SZ:20170630`
- `income:300959.SZ:20170930`
- `balancesheet:300959.SZ:20170930`
- `cashflow:300959.SZ:20170930`
- `income:300959.SZ:20180331`
- `balancesheet:300959.SZ:20180331`
- `cashflow:300959.SZ:20180331`
- `income:300959.SZ:20180630`
- `balancesheet:300959.SZ:20180630`
- `cashflow:300959.SZ:20180630`
- `income:300959.SZ:20180930`
- `balancesheet:300959.SZ:20180930`
- `cashflow:300959.SZ:20180930`
- `income:300959.SZ:20190331`
- `balancesheet:300959.SZ:20190331`
- `cashflow:300959.SZ:20190331`
- `income:300959.SZ:20190630`
- `balancesheet:300959.SZ:20190630`
- `cashflow:300959.SZ:20190630`
- `income:300959.SZ:20190930`
- `balancesheet:300959.SZ:20190930`
- `cashflow:300959.SZ:20190930`
- `balancesheet:300959.SZ:20200331`
- `balancesheet:300959.SZ:20200930`
- `balancesheet:300959.SZ:20210930`
- `balancesheet:002121.SZ:20211231`
- `balancesheet:002121.SZ:20220331`
- `income:300959.SZ:20240630`
- `balancesheet:002024.SZ:20150630`
- `income:002024.SZ:20150930`
- `balancesheet:000009.SZ:20160331`
- `income:002024.SZ:20160630`
- `balancesheet:002024.SZ:20190630`
- `cashflow:002024.SZ:20200930`
- `income:000009.SZ:20200930`
- `income:000009.SZ:20210930`
- `income:000009.SZ:20220630`
- `income:000009.SZ:20230630`
- `cashflow:000009.SZ:20230630`
- `balancesheet:002024.SZ:20240630`
- `income:002024.SZ:20250930`
- `cashflow:000568.SZ:20150630`
- `income:000501.SZ:20160331`
- `cashflow:000501.SZ:20170630`
- `income:000568.SZ:20181231`
- `balancesheet:000501.SZ:20190630`
- `income:000568.SZ:20240630`
- `balancesheet:000568.SZ:20241231`
- `balancesheet:000968.SZ:20160930`
- `balancesheet:000637.SZ:20170331`
- `cashflow:000968.SZ:20170331`
- `balancesheet:000968.SZ:20170630`
- `cashflow:000968.SZ:20181231`
- `balancesheet:000637.SZ:20210630`
- `balancesheet:000968.SZ:20210630`
- `balancesheet:000637.SZ:20210930`
- `cashflow:000968.SZ:20220630`
- `income:000637.SZ:20240630`
- `income:000968.SZ:20240630`
- `balancesheet:000968.SZ:20250930`
- `balancesheet:000795.SZ:20150331`
- `balancesheet:000795.SZ:20160331`
- `cashflow:000554.SZ:20160930`
- `balancesheet:000795.SZ:20180630`
- `cashflow:000795.SZ:20180630`
- `cashflow:000554.SZ:20181231`
- `balancesheet:000554.SZ:20200930`
- `income:000795.SZ:20210630`
- `cashflow:000554.SZ:20230630`
- `balancesheet:000795.SZ:20250930`
- `income:000795.SZ:20251231`
- `income:000713.SZ:20150331`
- `income:000713.SZ:20200930`
- `balancesheet:000713.SZ:20200930`
- `income:000850.SZ:20150331`
- `income:000850.SZ:20150630`
- `income:000869.SZ:20210630`
- `cashflow:000850.SZ:20220630`
- `cashflow:002021.SZ:20160331`
- `income:000025.SZ:20180630`
- `income:002021.SZ:20200331`
- `cashflow:000759.SZ:20230930`
- `income:000008.SZ:20160930`
- `cashflow:000008.SZ:20201231`
- `balancesheet:000702.SZ:20230331`
- `balancesheet:000001.SZ:20230630`
- `cashflow:002162.SZ:20240930`
- `balancesheet:000001.SZ:20250331`
- `cashflow:000505.SZ:20250630`
- `income:000612.SZ:20250930`
- `balancesheet:000612.SZ:20250930`
- `cashflow:000505.SZ:20250930`
- `balancesheet:600608.SH:20150630`
- `income:000551.SZ:20150630`
- `income:600608.SH:20160630`
- `income:600608.SH:20161231`
- `cashflow:000423.SZ:20170331`
- `balancesheet:000423.SZ:20170930`
- `income:000938.SZ:20191231`
- `balancesheet:000423.SZ:20200630`
- `income:600608.SH:20201231`
- `income:600608.SH:20210331`
- `balancesheet:600608.SH:20210331`
- `cashflow:000423.SZ:20211231`
- `income:600608.SH:20220630`
- `balancesheet:600608.SH:20230331`
- `cashflow:000506.SZ:20230930`
- `income:000551.SZ:20240930`
- `income:600608.SH:20251231`
- `balancesheet:000423.SZ:20251231`

Current interpretation:

- The required accounting-quality and asset-growth field groups pass despite these 149 empty statement requests because the combined statement table still has the required fields across the PIT rows.
- Offset 12 has a high empty-request count because `300959.SZ` has many pre-listing historical statement gaps; this is data availability, not signal strength.
- Shard 5 offset 6 produced 89 processed rows with 1 duplicate row in its summary; this carry-forward data-shape item must be checked before factor construction, not treated as alpha evidence.
- The latest three subshards had 0 duplicate rows and two empty statement requests, both from `000008.SZ`.
- Shard 5 is now complete with 20 symbols, 2,640 endpoint requests, 881 processed PIT rows, 24 empty statement requests, and aggregate PIT readiness passed.
- These empty requests must remain tracked; they are not alpha evidence and not promotion evidence.

## Latest Segment Evidence

Command:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 5 --symbol-offset 18 --symbol-limit 2 --max-endpoint-requests 300 --output-dir data\processed\round236_financial_statement_shard5_offset18_limit2_20260625
```

Result:

| Metric | Value |
|---|---:|
| Symbols | 2 |
| Periods | 44 |
| Endpoint requests | 264 |
| Processed rows | 88 |
| Empty requests | 0 |
| Required groups passing | 2 / 2 |
| Readiness blockers | 0 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Ann date range | 2015-04-28 to 2026-04-29 |

## Latest Three-Round Review

Scope: shard 5 offsets 14, 16, and 18.

- new symbols: 6;
- new endpoint requests: 792;
- new processed PIT rows: 264;
- new empty statement requests: 2;
- duplicate rows observed in source summaries: 0;
- required column groups: 2 / 2 for every subshard;
- aggregate readiness: passed;
- decision: pause blind shard 6 continuation until the Round237 formula smoke, deduplication check, and throughput gate pass.

Interpretation: these three subshards add six long-cycle PIT statement histories and no readiness blockers. Empty-request density remains low versus the shard 4 noisy segment, while duplicate rows were 0 in this latest group. The carry-forward duplicate-row warning from shard 5 offset 6 remains a pre-factor-construction data-quality item. The slow ordinary endpoint route remains the main throughput bottleneck. After the 100-symbol node, the better next step is no longer blind two-symbol continuation; it is a formula-smoke and throughput gate before spending more API quota. This still does not authorize factor preregistration, portfolio grids, promotion claims, or final holdout access.

## Shard 1 Closeout Audit

Shard 1 is complete:

- 20 / 20 symbols completed;
- 2,640 endpoint requests completed;
- 880 processed PIT statement rows written;
- 7 empty statement requests tracked;
- all ten subshards passed both required column groups.

Aggregate readiness:

- report: `data/reports/round236_financial_statement_shard1_aggregate_readiness_20260625/tushare_financial_pit_readiness.json`;
- files scanned: 2,790;
- financial-like datasets: 2,770;
- PIT-ready datasets: 2,760;
- required column groups passing: 2 / 2;
- blockers: 0;
- pass: true.

Note: the 10 financial-like datasets not marked PIT-ready are the per-subshard JSON summary files, not the parquet statement inputs used by the required accounting-quality groups.

Audit interpretation:

- This is useful data-foundation progress, not a discovered alpha.
- Empty-request rate is low enough to continue, but every empty request remains a data-quality item.
- No factor preregistration, portfolio grid, walk-forward claim, promotion claim, or final holdout access is allowed from this shard alone.
- Direction remains accounting accruals/cashflow quality, because it addresses the earlier weakness of over-mining one moneyflow family and gives a better economic prior.

## Shard 2 Closeout Audit

Shard 2 is complete:

- 20 / 20 symbols completed;
- 2,640 endpoint requests completed;
- 880 processed PIT statement rows written;
- 7 empty statement requests tracked;
- all ten subshards passed both required column groups.

Aggregate readiness:

- report: `data/reports/round236_financial_statement_shard2_aggregate_readiness_20260625/tushare_financial_pit_readiness.json`;
- files scanned: 2,790;
- financial-like datasets: 2,770;
- PIT-ready datasets: 2,760;
- required column groups passing: 2 / 2;
- blockers: 0;
- pass: true.

Note: the 10 financial-like datasets not marked PIT-ready are the per-subshard JSON summary files, not the parquet statement inputs used by the required accounting-quality groups.

Audit interpretation:

- Shard 2 confirms the ordinary per-symbol route is viable but slow.
- Empty-request handling remains a data-quality control, not a signal.
- The next optimization target is throughput and resume safety for full-universe statement coverage.

## Shard 3 Closeout Audit

Shard 3 is complete:

- 20 / 20 symbols completed;
- 2,640 endpoint requests completed;
- 880 processed PIT statement rows written;
- 19 empty statement requests tracked;
- all ten subshards passed both required column groups.

Aggregate readiness:

- report: `data/reports/round236_financial_statement_shard3_aggregate_readiness_20260625/tushare_financial_pit_readiness.json`;
- files scanned: 2,790;
- financial-like datasets: 2,770;
- PIT-ready datasets: 2,760;
- required column groups passing: 2 / 2;
- blockers: 0;
- pass: true.

Audit interpretation:

- Shard 3 confirms the accounting-quality data path continues to work across another full 20-symbol shard.
- The empty-request count is higher than shards 1 and 2, but it remains sparse enough to continue with explicit tracking.
- No alpha, portfolio, promotion, or holdout claim is authorized from this data-foundation closeout alone.

## Shard 4 Closeout Audit

Shard 4 is complete:

- 20 / 20 symbols completed;
- 2,640 endpoint requests completed;
- 866 processed PIT statement rows written;
- 105 empty statement requests tracked;
- all ten subshards passed both required column groups.

Aggregate readiness:

- report: `data/reports/round236_financial_statement_shard4_aggregate_readiness_20260625/tushare_financial_pit_readiness.json`;
- files scanned: 2,790;
- financial-like datasets: 2,770;
- PIT-ready datasets: 2,760;
- required column groups passing: 2 / 2;
- blockers: 0;
- pass: true.

Audit interpretation:

- Shard 4 confirms the statement route can survive a noisier shard, including the high empty-request count from `300959.SZ` pre-listing gaps.
- The lower processed row count versus shards 1-3 is a coverage/data-availability item to model explicitly before factor construction.
- This closeout improves confidence in the PIT data foundation, but it still does not constitute an alpha, a portfolio result, or promotion evidence.

## Shard 5 Closeout Audit

Shard 5 is complete:

- 20 / 20 symbols completed;
- 2,640 endpoint requests completed;
- 881 processed PIT statement rows written;
- 24 empty statement requests tracked;
- all ten subshards passed both required column groups.

Aggregate readiness:

- report: `data/reports/round236_financial_statement_shard5_aggregate_readiness_20260625/tushare_financial_pit_readiness.json`;
- files scanned: 2,790;
- financial-like datasets: 2,770;
- PIT-ready datasets: 2,760;
- required column groups passing: 2 / 2;
- blockers: 0;
- pass: true.

Audit interpretation:

- Shard 5 confirms the statement route can complete another full 20-symbol shard with lower empty-request density than shard 4.
- The one duplicate-row/data-shape warning from shard 5 offset 6 remains a pre-factor-construction control item even though the shard-level required groups pass.
- The 100-symbol cumulative node improves the data foundation for accounting accruals/cashflow quality, but it still does not constitute an alpha, a portfolio result, or promotion evidence.

## Round237 Method Gate

Round237 adds an efficiency and formula-smoke gate before more broad backfill.

Coverage at the 100-symbol node:

| Item | Value |
|---|---:|
| Completed symbols | 100 / 5,208 |
| Symbol coverage | 1.9201% |
| Completed endpoint requests | 13,200 / 687,456 |
| Endpoint coverage | 1.9201% |
| Remaining endpoint requests | 674,256 |
| Remaining two-symbol subshards | 2,554 |
| Empty requests | 149 |
| Empty-request rate | 1.1288% |

Repeatable formula-smoke result over the completed 100 symbols, without return labels:

| Item | Value |
|---|---:|
| Source files scanned | 600 |
| Statement rows before dedup | 4,387 |
| Statement rows after dedup | 4,386 |
| Duplicate statement keys | 1 |
| Blockers | 0 |

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 4,286 | 97.72% | 100 |
| `cashflow_minus_netprofit_to_assets_raw` | 4,286 | 97.72% | 100 |
| `low_asset_growth_quality_raw` | 3,919 | 89.3525% | 100 |
| `working_capital_accruals_to_assets_raw` | 3,836 | 87.4601% | 98 |
| `earnings_cash_conversion_improvement_yoy_raw` | 3,813 | 86.9357% | 100 |

Cumulative formula-smoke result after shard 6 offsets 0, 5, and 10 with the original pilot first2 included:

| Item | Value |
|---|---:|
| Source roots | 53 |
| Source files | 636 |
| Statement rows before dedup | 5,048 |
| Statement rows after dedup | 5,046 |
| Unique symbols | 115 |
| Duplicate statement keys | 2 |
| Blockers | 0 |

| Candidate formula | Valid rows | Coverage | Symbols |
|---|---:|---:|---:|
| `low_total_accruals_to_assets_raw` | 4,922 | 97.5426% | 115 |
| `cashflow_minus_netprofit_to_assets_raw` | 4,922 | 97.5426% | 115 |
| `low_asset_growth_quality_raw` | 4,503 | 89.2390% | 115 |
| `working_capital_accruals_to_assets_raw` | 4,383 | 86.8609% | 112 |
| `earnings_cash_conversion_improvement_yoy_raw` | 4,374 | 86.6825% | 115 |

Audit conclusion:

- the accounting-quality statement fields can generate the intended formula family;
- one duplicate `asset_id/end_date/ann_date/report_type` key must be handled before factor matrix persistence;
- existing PEAD/fina_indicator tooling is not directly compatible because it expects fields such as `netprofit_yoy` rather than statement fields such as `netprofit`, `n_cashflow_act`, and `total_assets`;
- formula coverage alone is not profitability evidence and does not authorize preregistration, IC claims, portfolio grids, promotion, or final holdout access.

Round237 method files:

- `src/quant_robot/ops/accounting_quality_statement_formula_smoke.py`
- `scripts/run_accounting_quality_statement_formula_smoke.py`
- `tests/unit/test_accounting_quality_statement_formula_smoke.py`
- `tests/unit/test_accounting_quality_statement_formula_smoke_cli.py`
- `configs/accounting_quality_statement_smoke_plan_round237_20260625.json`
- `docs/research/cn_stock_round237_accounting_quality_100_symbol_efficiency_audit_2026-06-25.md`

## Next Action

The Round237/Round238 formula-smoke path and three non-overlapping `symbol_limit=5` throughput gates passed. Continue shard 6 from the next non-overlapping subshard:

```text
shard_id=6, symbol_offset=15, symbol_limit=5
```

Planned symbols:

- `300106.SZ`
- `000681.SZ`
- `000927.SZ`
- `000421.SZ`
- `601601.SH`

Before running it or a larger subshard, complete:

- keep the repeatable statement-accounting-quality formula smoke passing;
- keep deduplication of `asset_id/end_date/ann_date/report_type` enabled;
- PIT signal-date rule: first tradable date after `ann_date`, no same-day close execution;
- keep `symbol_limit=5` until at least one more non-overlapping subshard passes the same readiness and formula-smoke gates.

Continue to block:

- accounting-quality factor preregistration from the 100-symbol smoke alone;
- IC and portfolio grids before label alignment and sufficient cross-section coverage;
- promotion claims;
- final holdout access.

## Verification

Commands run:

```powershell
python -m json.tool configs\accounting_quality_statement_backfill_round236_20260625.json > $null
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_pilot_first2_fullcycle_20260625 --root data\processed\round236_financial_statement_shard1_offset2_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset4_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset6_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset8_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset10_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset12_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset14_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset16_limit2_20260625 --root data\processed\round236_financial_statement_shard1_offset18_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard1_aggregate_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard2_offset0_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset2_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset4_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset6_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset8_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset10_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset12_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset14_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset16_limit2_20260625 --root data\processed\round236_financial_statement_shard2_offset18_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard2_aggregate_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard3_offset0_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset2_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset4_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard3_offsets0_2_4_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard3_offset6_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset8_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset10_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard3_offsets6_8_10_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard3_offset12_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset14_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset16_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard3_offsets12_14_16_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard3_offset0_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset2_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset4_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset6_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset8_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset10_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset12_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset14_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset16_limit2_20260625 --root data\processed\round236_financial_statement_shard3_offset18_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard3_aggregate_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard3_offset18_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset0_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset2_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard3_offset18_shard4_offsets0_2_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard4_offset4_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset6_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset8_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard4_offsets4_6_8_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard4_offset10_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset12_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset14_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard4_offsets10_12_14_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard4_offset16_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset18_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset0_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard4_offsets16_18_shard5_offset0_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard4_offset0_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset2_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset4_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset6_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset8_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset10_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset12_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset14_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset16_limit2_20260625 --root data\processed\round236_financial_statement_shard4_offset18_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard4_aggregate_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard5_offset2_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset4_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset6_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard5_offsets2_4_6_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard5_offset8_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset10_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset12_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard5_offsets8_10_12_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard5_offset14_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset16_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset18_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard5_offsets14_16_18_readiness_20260625
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\round236_financial_statement_shard5_offset0_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset2_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset4_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset6_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset8_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset10_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset12_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset14_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset16_limit2_20260625 --root data\processed\round236_financial_statement_shard5_offset18_limit2_20260625 --required-column-group accounting_accrual_quality:netprofit,n_cashflow_act,total_assets --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab --output-dir data\reports\round236_financial_statement_shard5_aggregate_readiness_20260625
python -m unittest tests.unit.test_financial_statement_shard_backfill_cli tests.unit.test_financial_statement_limited_backfill_smoke_cli tests.unit.test_tushare_financial_statement_ingest tests.unit.test_tushare_financial_pit_readiness tests.unit.test_tushare_financial_pit_readiness_cli tests.unit.test_financial_statement_symbol_shard_plan tests.unit.test_financial_statement_symbol_shard_plan_cli
git diff --check -- configs\accounting_quality_statement_backfill_round236_20260625.json docs\research\cn_stock_round236_financial_statement_shard_progress_2026-06-25.md
```

Verification passed:

- JSON syntax check passed.
- Aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 2 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 3 offsets 0/2/4 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 3 offsets 6/8/10 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 3 offsets 12/14/16 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 3 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 3 offset18 plus shard 4 offsets 0/2 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 4 offsets 4/6/8 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 4 offsets 10/12/14 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 4 offsets 16/18 plus shard 5 offset 0 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 4 full aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 5 offsets 2/4/6 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 5 offsets 8/10/12 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 5 offsets 14/16/18 aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- Shard 5 full aggregate PIT readiness check passed with blockers 0 and required column groups 2 / 2.
- 20 relevant unit tests passed.
- Diff whitespace check passed for the updated progress config and report.
