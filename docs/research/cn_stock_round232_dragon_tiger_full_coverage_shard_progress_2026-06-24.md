# CN Stock Round232 Dragon-Tiger Full Coverage Shard Progress - 2026-06-24

## Scope

Round232 is still in the data-coverage gate. It has not reached PIT IC, portfolio backtest, walk-forward, or promotion.

This report records the reusable Dragon-Tiger coverage audit implementation and the first one hundred thirty-two formal long-cycle shards:

- `top_list`: Tushare Dragon-Tiger abnormal trading list by `trade_date`;
- `top_inst`: Tushare Dragon-Tiger institutional seat detail by `trade_date`;
- event availability: first open trade date strictly after `trade_date`;
- same-day disclosure trading: forbidden.

## Implemented Repeatable Entry Point

Code:

```text
src/quant_robot/ops/dragon_tiger_coverage_audit.py
scripts/run_dragon_tiger_coverage_audit.py
```

Adapter additions:

```text
TushareAdapter.fetch_top_list_by_trade_date
TushareAdapter.fetch_top_inst_by_trade_date
```

Unit coverage:

```text
tests/unit/test_dragon_tiger_coverage_audit.py
tests/unit/test_tushare_adapter.py
```

The audit writes normalized row-level caches and a stock-day aggregate when `--execute-write-processed` is supplied:

```text
processed/dragon_tiger_top_list
processed/dragon_tiger_top_inst
processed/dragon_tiger_stock_day
```

The stock-day aggregate preserves event counts and reason counts, so multiple Dragon-Tiger reasons or institutional seats on the same stock-date are not collapsed into a single blind value.

The calendar fetch path now retries transient empty open-calendar responses before failing. This was added after a live `2015-04` shard attempt received an empty Tushare calendar response while an immediate direct retry returned 21 open trade dates.

## Live Smoke

Window:

```text
2024-01-02 to 2024-01-05
```

Result:

- calendar trade dates: 4;
- `top_list`: 250 rows, 4 / 4 non-empty dates;
- `top_inst`: 2,766 rows, 4 / 4 non-empty dates;
- stock-day aggregate: 247 rows, 160 symbols;
- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- PIT prescreen allowed for this smoke only: true;
- portfolio / promotion allowed: false.

## Formal Long-Cycle Shards Completed

Processed root:

```text
data/processed/round232_dragon_tiger_attention_reversal_20260624
```

Report root:

```text
data/reports/round232_dragon_tiger_attention_reversal_20260624/full_coverage_shards
```

| Shard | Window | Trade Dates | top_list Rows | top_list Non-empty | top_inst Rows | top_inst Non-empty | Stock-day Rows | Lag Violations | Missing Available | Blockers |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `shard_201501` | 2015-01-01 to 2015-01-31 | 20 | 849 | 20 | 8,252 | 19 | 781 | 0 | 0 | none |
| `shard_201502` | 2015-02-01 to 2015-02-28 | 15 | 686 | 15 | 6,644 | 14 | 631 | 0 | 0 | none |
| `shard_201503` | 2015-03-01 to 2015-03-31 | 22 | 1,156 | 21 | 12,539 | 22 | 1,107 | 0 | 0 | none |
| `shard_201504` | 2015-04-01 to 2015-04-30 | 21 | 1,555 | 21 | 15,923 | 21 | 1,444 | 0 | 0 | none |
| `shard_201505` | 2015-05-01 to 2015-05-31 | 20 | 1,956 | 20 | 20,117 | 20 | 1,825 | 0 | 0 | none |
| `shard_201506` | 2015-06-01 to 2015-06-30 | 21 | 2,098 | 21 | 21,888 | 21 | 1,927 | 0 | 0 | none |
| `shard_201507` | 2015-07-01 to 2015-07-31 | 23 | 2,844 | 23 | 29,188 | 23 | 2,640 | 0 | 0 | none |
| `shard_201508` | 2015-08-01 to 2015-08-31 | 21 | 1,531 | 21 | 15,850 | 20 | 1,399 | 0 | 0 | none |
| `shard_201509` | 2015-09-01 to 2015-09-30 | 20 | 1,678 | 20 | 17,424 | 20 | 1,499 | 0 | 0 | none |
| `shard_201510` | 2015-10-01 to 2015-10-31 | 17 | 1,004 | 16 | 11,100 | 16 | 970 | 0 | 0 | none |
| `shard_201511` | 2015-11-01 to 2015-11-30 | 21 | 1,310 | 21 | 13,864 | 21 | 1,203 | 0 | 0 | none |
| `shard_201512` | 2015-12-01 to 2015-12-31 | 23 | 1,433 | 23 | 14,319 | 22 | 1,322 | 0 | 0 | none |
| `shard_201601` | 2016-01-01 to 2016-01-31 | 20 | 1,309 | 20 | 13,768 | 20 | 1,159 | 0 | 0 | none |
| `shard_201602` | 2016-02-01 to 2016-02-29 | 16 | 845 | 16 | 8,951 | 16 | 773 | 0 | 0 | none |
| `shard_201603` | 2016-03-01 to 2016-03-31 | 23 | 996 | 23 | 10,012 | 22 | 940 | 0 | 0 | none |
| `shard_201604` | 2016-04-01 to 2016-04-30 | 20 | 922 | 20 | 9,558 | 20 | 846 | 0 | 0 | none |
| `shard_201605` | 2016-05-01 to 2016-05-31 | 21 | 931 | 21 | 9,478 | 21 | 861 | 0 | 0 | none |
| `shard_201606` | 2016-06-01 to 2016-06-30 | 20 | 916 | 20 | 9,352 | 20 | 849 | 0 | 0 | none |
| `shard_201607` | 2016-07-01 to 2016-07-31 | 21 | 975 | 20 | 10,282 | 21 | 930 | 0 | 0 | none |
| `shard_201608` | 2016-08-01 to 2016-08-31 | 23 | 1,061 | 23 | 10,478 | 23 | 956 | 0 | 0 | none |
| `shard_201609` | 2016-09-01 to 2016-09-30 | 20 | 902 | 20 | 8,831 | 20 | 809 | 0 | 0 | none |
| `shard_201610` | 2016-10-01 to 2016-10-31 | 16 | 779 | 16 | 7,666 | 16 | 695 | 0 | 0 | none |
| `shard_201611` | 2016-11-01 to 2016-11-30 | 22 | 1,117 | 22 | 11,483 | 22 | 1,014 | 0 | 0 | none |
| `shard_201612` | 2016-12-01 to 2016-12-31 | 22 | 1,188 | 22 | 12,221 | 22 | 1,063 | 0 | 0 | none |
| `shard_201701` | 2017-01-01 to 2017-01-31 | 18 | 1,031 | 18 | 10,452 | 18 | 921 | 0 | 0 | none |
| `shard_201702` | 2017-02-01 to 2017-02-28 | 18 | 946 | 18 | 9,640 | 18 | 861 | 0 | 0 | none |
| `shard_201703` | 2017-03-01 to 2017-03-31 | 23 | 1,141 | 23 | 13,394 | 23 | 1,013 | 0 | 0 | none |
| `shard_201704` | 2017-04-01 to 2017-04-30 | 18 | 1,199 | 18 | 12,460 | 18 | 1,078 | 0 | 0 | none |
| `shard_201705` | 2017-05-01 to 2017-05-31 | 20 | 1,262 | 20 | 12,878 | 20 | 1,132 | 0 | 0 | none |
| `shard_201706` | 2017-06-01 to 2017-06-30 | 22 | 1,082 | 22 | 10,886 | 22 | 965 | 0 | 0 | none |
| `shard_201707` | 2017-07-01 to 2017-07-31 | 21 | 1,006 | 21 | 9,932 | 21 | 913 | 0 | 0 | none |
| `shard_201708` | 2017-08-01 to 2017-08-31 | 23 | 1,042 | 23 | 10,754 | 23 | 944 | 0 | 0 | none |
| `shard_201709` | 2017-09-01 to 2017-09-30 | 21 | 1,067 | 21 | 10,892 | 21 | 952 | 0 | 0 | none |
| `shard_201710` | 2017-10-01 to 2017-10-31 | 17 | 841 | 17 | 8,579 | 17 | 740 | 0 | 0 | none |
| `shard_201711` | 2017-11-01 to 2017-11-30 | 22 | 1,194 | 22 | 11,969 | 22 | 1,086 | 0 | 0 | none |
| `shard_201712` | 2017-12-01 to 2017-12-31 | 21 | 954 | 21 | 9,833 | 21 | 864 | 0 | 0 | none |
| `shard_201801` | 2018-01-01 to 2018-01-31 | 22 | 1,216 | 22 | 18,281 | 22 | 1,013 | 0 | 0 | none |
| `shard_201802` | 2018-02-01 to 2018-02-28 | 15 | 973 | 15 | 10,192 | 15 | 874 | 0 | 0 | none |
| `shard_201803` | 2018-03-01 to 2018-03-31 | 22 | 1,069 | 22 | 11,408 | 22 | 964 | 0 | 0 | none |
| `shard_201804` | 2018-04-01 to 2018-04-30 | 18 | 1,060 | 18 | 11,212 | 18 | 961 | 0 | 0 | none |
| `shard_201805` | 2018-05-01 to 2018-05-31 | 22 | 1,206 | 22 | 13,129 | 22 | 1,088 | 0 | 0 | none |
| `shard_201806` | 2018-06-01 to 2018-06-30 | 20 | 1,329 | 20 | 13,937 | 20 | 1,181 | 0 | 0 | none |
| `shard_201807` | 2018-07-01 to 2018-07-31 | 22 | 1,429 | 22 | 15,141 | 22 | 1,287 | 0 | 0 | none |
| `shard_201808` | 2018-08-01 to 2018-08-31 | 23 | 1,298 | 23 | 13,271 | 23 | 1,158 | 0 | 0 | none |
| `shard_201809` | 2018-09-01 to 2018-09-30 | 19 | 984 | 19 | 10,141 | 19 | 873 | 0 | 0 | none |
| `shard_201810` | 2018-10-01 to 2018-10-31 | 18 | 1,147 | 18 | 12,046 | 18 | 1,020 | 0 | 0 | none |
| `shard_201811` | 2018-11-01 to 2018-11-30 | 22 | 1,273 | 22 | 13,824 | 22 | 1,159 | 0 | 0 | none |
| `shard_201812` | 2018-12-01 to 2018-12-31 | 20 | 970 | 20 | 10,286 | 20 | 881 | 0 | 0 | none |
| `shard_201901` | 2019-01-01 to 2019-01-31 | 22 | 1,569 | 22 | 26,350 | 22 | 1,129 | 0 | 0 | none |
| `shard_201902` | 2019-02-01 to 2019-02-28 | 15 | 996 | 15 | 17,006 | 15 | 741 | 0 | 0 | none |
| `shard_201903` | 2019-03-01 to 2019-03-31 | 21 | 1,866 | 21 | 32,186 | 21 | 1,387 | 0 | 0 | none |
| `shard_201904` | 2019-04-01 to 2019-04-30 | 21 | 1,917 | 21 | 32,850 | 21 | 1,373 | 0 | 0 | none |
| `shard_201905` | 2019-05-01 to 2019-05-31 | 20 | 1,782 | 20 | 30,205 | 20 | 1,297 | 0 | 0 | none |
| `shard_201906` | 2019-06-01 to 2019-06-30 | 19 | 1,535 | 19 | 26,406 | 19 | 1,109 | 0 | 0 | none |
| `shard_201907` | 2019-07-01 to 2019-07-31 | 23 | 1,319 | 23 | 22,672 | 23 | 1,014 | 0 | 0 | none |
| `shard_201908` | 2019-08-01 to 2019-08-31 | 22 | 1,340 | 22 | 23,757 | 22 | 1,043 | 0 | 0 | none |
| `shard_201909` | 2019-09-01 to 2019-09-30 | 20 | 1,277 | 20 | 21,755 | 20 | 951 | 0 | 0 | none |
| `shard_201910` | 2019-10-01 to 2019-10-31 | 18 | 1,302 | 18 | 21,406 | 18 | 952 | 0 | 0 | none |
| `shard_201911` | 2019-11-01 to 2019-11-30 | 21 | 1,454 | 21 | 23,787 | 21 | 1,036 | 0 | 0 | none |
| `shard_201912` | 2019-12-01 to 2019-12-31 | 22 | 1,457 | 22 | 22,630 | 21 | 1,073 | 0 | 0 | none |
| `shard_202001` | 2020-01-01 to 2020-01-31 | 16 | 1,195 | 16 | 18,169 | 16 | 906 | 0 | 0 | none |
| `shard_202002` | 2020-02-01 to 2020-02-29 | 20 | 1,994 | 20 | 31,351 | 20 | 1,583 | 0 | 0 | none |
| `shard_202003` | 2020-03-01 to 2020-03-31 | 22 | 1,971 | 22 | 31,478 | 22 | 1,507 | 0 | 0 | none |
| `shard_202004` | 2020-04-01 to 2020-04-30 | 21 | 1,704 | 21 | 26,055 | 21 | 1,256 | 0 | 0 | none |
| `shard_202005` | 2020-05-01 to 2020-05-31 | 18 | 1,706 | 18 | 24,239 | 18 | 1,231 | 0 | 0 | none |
| `shard_202006` | 2020-06-01 to 2020-06-30 | 20 | 1,658 | 20 | 24,295 | 20 | 1,323 | 0 | 0 | none |
| `shard_202007` | 2020-07-01 to 2020-07-31 | 23 | 2,284 | 23 | 32,226 | 23 | 1,788 | 0 | 0 | none |
| `shard_202008` | 2020-08-01 to 2020-08-31 | 21 | 1,895 | 21 | 29,098 | 21 | 1,506 | 0 | 0 | none |
| `shard_202009` | 2020-09-01 to 2020-09-30 | 22 | 1,547 | 22 | 22,508 | 22 | 1,151 | 0 | 0 | none |
| `shard_202010` | 2020-10-01 to 2020-10-31 | 16 | 868 | 16 | 13,824 | 16 | 694 | 0 | 0 | none |
| `shard_202011` | 2020-11-01 to 2020-11-30 | 21 | 1,261 | 21 | 19,651 | 21 | 1,018 | 0 | 0 | none |
| `shard_202012` | 2020-12-01 to 2020-12-31 | 23 | 1,637 | 23 | 23,679 | 23 | 1,246 | 0 | 0 | none |
| `shard_202101` | 2021-01-01 to 2021-01-31 | 20 | 1,782 | 20 | 26,158 | 20 | 1,373 | 0 | 0 | none |
| `shard_202102` | 2021-02-01 to 2021-02-28 | 15 | 1,518 | 15 | 20,830 | 15 | 1,120 | 0 | 0 | none |
| `shard_202103` | 2021-03-01 to 2021-03-31 | 23 | 1,818 | 23 | 25,299 | 22 | 1,366 | 0 | 0 | none |
| `shard_202104` | 2021-04-01 to 2021-04-30 | 21 | 1,477 | 21 | 22,354 | 21 | 1,181 | 0 | 0 | none |
| `shard_202105` | 2021-05-01 to 2021-05-31 | 18 | 1,481 | 18 | 18,795 | 18 | 1,084 | 0 | 0 | none |
| `shard_202106` | 2021-06-01 to 2021-06-30 | 21 | 1,486 | 21 | 20,291 | 21 | 1,214 | 0 | 0 | none |
| `shard_202107` | 2021-07-01 to 2021-07-31 | 22 | 1,682 | 22 | 22,027 | 22 | 1,310 | 0 | 0 | none |
| `shard_202108` | 2021-08-01 to 2021-08-31 | 22 | 1,600 | 21 | 23,295 | 22 | 1,322 | 0 | 0 | none |
| `shard_202109` | 2021-09-01 to 2021-09-30 | 20 | 1,412 | 20 | 20,723 | 20 | 1,205 | 0 | 0 | none |
| `shard_202110` | 2021-10-01 to 2021-10-31 | 16 | 1,152 | 16 | 15,576 | 16 | 910 | 0 | 0 | none |
| `shard_202111` | 2021-11-01 to 2021-11-30 | 22 | 1,460 | 22 | 21,071 | 22 | 1,253 | 0 | 0 | none |
| `shard_202112` | 2021-12-01 to 2021-12-31 | 23 | 1,647 | 23 | 24,602 | 23 | 1,343 | 0 | 0 | none |
| `shard_202201` | 2022-01-01 to 2022-01-31 | 19 | 1,611 | 19 | 23,781 | 19 | 1,340 | 0 | 0 | none |
| `shard_202202` | 2022-02-01 to 2022-02-28 | 16 | 1,123 | 16 | 16,901 | 16 | 897 | 0 | 0 | none |
| `shard_202203` | 2022-03-01 to 2022-03-31 | 23 | 1,674 | 23 | 24,074 | 23 | 1,309 | 0 | 0 | none |
| `shard_202204` | 2022-04-01 to 2022-04-30 | 19 | 1,872 | 19 | 23,147 | 18 | 1,420 | 0 | 0 | none |
| `shard_202205` | 2022-05-01 to 2022-05-31 | 19 | 1,665 | 19 | 23,662 | 19 | 1,392 | 0 | 0 | none |
| `shard_202206` | 2022-06-01 to 2022-06-30 | 21 | 1,918 | 21 | 25,113 | 21 | 1,684 | 0 | 0 | none |
| `shard_202207` | 2022-07-01 to 2022-07-31 | 21 | 1,469 | 21 | 16,577 | 21 | 1,264 | 0 | 0 | none |
| `shard_202208` | 2022-08-01 to 2022-08-31 | 23 | 1,593 | 23 | 19,063 | 23 | 1,335 | 0 | 0 | none |
| `shard_202209` | 2022-09-01 to 2022-09-30 | 21 | 1,111 | 21 | 10,882 | 21 | 999 | 0 | 0 | none |
| `shard_202210` | 2022-10-01 to 2022-10-31 | 16 | 1,017 | 16 | 9,848 | 16 | 916 | 0 | 0 | none |
| `shard_202211` | 2022-11-01 to 2022-11-30 | 22 | 1,301 | 22 | 13,024 | 22 | 1,132 | 0 | 0 | none |
| `shard_202212` | 2022-12-01 to 2022-12-31 | 22 | 1,288 | 22 | 12,313 | 22 | 1,087 | 0 | 0 | none |
| `shard_202301` | 2023-01-01 to 2023-01-31 | 16 | 764 | 16 | 7,436 | 16 | 653 | 0 | 0 | none |
| `shard_202302` | 2023-02-01 to 2023-02-28 | 20 | 1,022 | 20 | 10,030 | 20 | 878 | 0 | 0 | none |
| `shard_202303` | 2023-03-01 to 2023-03-31 | 23 | 1,180 | 23 | 11,373 | 23 | 1,009 | 0 | 0 | none |
| `shard_202304` | 2023-04-01 to 2023-04-30 | 19 | 1,410 | 19 | 13,192 | 19 | 1,157 | 0 | 0 | none |
| `shard_202305` | 2023-05-01 to 2023-05-31 | 20 | 1,583 | 20 | 14,760 | 20 | 1,365 | 0 | 0 | none |
| `shard_202306` | 2023-06-01 to 2023-06-30 | 20 | 1,530 | 20 | 14,360 | 20 | 1,371 | 0 | 0 | none |
| `shard_202307` | 2023-07-01 to 2023-07-31 | 21 | 1,313 | 21 | 13,288 | 21 | 1,158 | 0 | 0 | none |
| `shard_202308` | 2023-08-01 to 2023-08-31 | 23 | 1,436 | 23 | 13,975 | 23 | 1,209 | 0 | 0 | none |
| `shard_202309` | 2023-09-01 to 2023-09-30 | 20 | 1,139 | 20 | 11,495 | 20 | 947 | 0 | 0 | none |
| `shard_202310` | 2023-10-01 to 2023-10-31 | 17 | 1,048 | 16 | 10,110 | 16 | 910 | 0 | 0 | none |
| `shard_202311` | 2023-11-01 to 2023-11-30 | 22 | 1,541 | 22 | 16,097 | 22 | 1,485 | 0 | 0 | none |
| `shard_202312` | 2023-12-01 to 2023-12-31 | 21 | 1,461 | 21 | 15,229 | 21 | 1,432 | 0 | 0 | none |
| `shard_202401` | 2024-01-01 to 2024-01-31 | 22 | 1,430 | 22 | 15,142 | 22 | 1,380 | 0 | 0 | none |
| `shard_202402` | 2024-02-01 to 2024-02-29 | 15 | 2,419 | 15 | 20,150 | 15 | 2,217 | 0 | 0 | none |
| `shard_202403` | 2024-03-01 to 2024-03-31 | 21 | 1,566 | 21 | 15,122 | 21 | 1,395 | 0 | 0 | none |
| `shard_202404` | 2024-04-01 to 2024-04-30 | 20 | 1,909 | 20 | 17,554 | 20 | 1,601 | 0 | 0 | none |
| `shard_202405` | 2024-05-01 to 2024-05-31 | 20 | 1,647 | 20 | 17,027 | 20 | 1,497 | 0 | 0 | none |
| `shard_202406` | 2024-06-01 to 2024-06-30 | 19 | 1,554 | 19 | 16,156 | 19 | 1,409 | 0 | 0 | none |
| `shard_202407` | 2024-07-01 to 2024-07-31 | 23 | 1,528 | 23 | 15,389 | 23 | 1,472 | 0 | 0 | none |
| `shard_202408` | 2024-08-01 to 2024-08-31 | 22 | 1,391 | 22 | 14,934 | 22 | 1,330 | 0 | 0 | none |
| `shard_202409` | 2024-09-01 to 2024-09-30 | 19 | 1,128 | 19 | 12,109 | 19 | 1,046 | 0 | 0 | none |
| `shard_202410` | 2024-10-01 to 2024-10-31 | 18 | 2,176 | 18 | 22,393 | 18 | 2,141 | 0 | 0 | none |
| `shard_202411` | 2024-11-01 to 2024-11-30 | 21 | 2,295 | 21 | 24,844 | 21 | 2,230 | 0 | 0 | none |
| `shard_202412` | 2024-12-01 to 2024-12-31 | 22 | 1,868 | 22 | 20,533 | 22 | 1,790 | 0 | 0 | none |
| `shard_202501` | 2025-01-01 to 2025-01-31 | 18 | 1,313 | 18 | 14,396 | 18 | 1,266 | 0 | 0 | none |
| `shard_202502` | 2025-02-01 to 2025-02-28 | 18 | 1,436 | 18 | 15,716 | 18 | 1,389 | 0 | 0 | none |
| `shard_202503` | 2025-03-01 to 2025-03-31 | 21 | 1,537 | 21 | 16,945 | 21 | 1,516 | 0 | 0 | none |
| `shard_202504` | 2025-04-01 to 2025-04-30 | 21 | 1,480 | 18 | 18,544 | 21 | 1,660 | 0 | 0 | none |
| `shard_202505` | 2025-05-01 to 2025-05-31 | 19 | 1,436 | 19 | 15,579 | 19 | 1,389 | 0 | 0 | none |
| `shard_202506` | 2025-06-01 to 2025-06-30 | 20 | 1,479 | 20 | 16,307 | 20 | 1,449 | 0 | 0 | none |
| `shard_202507` | 2025-07-01 to 2025-07-31 | 23 | 1,700 | 23 | 18,292 | 23 | 1,647 | 0 | 0 | none |
| `shard_202508` | 2025-08-01 to 2025-08-31 | 21 | 1,573 | 21 | 16,699 | 21 | 1,527 | 0 | 0 | none |
| `shard_202509` | 2025-09-01 to 2025-09-30 | 22 | 1,561 | 22 | 16,636 | 22 | 1,515 | 0 | 0 | none |
| `shard_202510` | 2025-10-01 to 2025-10-31 | 17 | 1,177 | 17 | 12,656 | 17 | 1,072 | 0 | 0 | none |
| `shard_202511` | 2025-11-01 to 2025-11-30 | 20 | 1,472 | 20 | 15,722 | 20 | 1,324 | 0 | 0 | none |
| `shard_202512` | 2025-12-01 to 2025-12-31 | 23 | 1,639 | 23 | 17,798 | 23 | 1,498 | 0 | 0 | none |

Warnings are expected at this gate:

- duplicate stock-date-reason or seat-level rows are retained and aggregated later;
- `top_inst` buy/sell side fields can be missing on the opposite side;
- early `top_list` `float_values`/`l_sell` fields can be partially missing.
- `top_inst` can have occasional empty event dates; these are retained as warnings when the non-empty ratio clears the gate.

These warnings do not waive the full-coverage requirement.

## Three-Shard Review: 2015-10 to 2015-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- holiday and year-end availability handling passed: `2015-10` resumes at `2015-10-09`, and `2015-12` rolls availability into `2016-01-04`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 1 date, `20151026`;
- `top_inst` empty event dates in this batch: 2 dates, `20151009` and `20151217`;
- non-empty ratios stayed above the 0.8 gate for every endpoint shard.

## Three-Shard Review: 2016-01 to 2016-03

This three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- stress-regime coverage added: `2016-01` covers the A-share circuit-breaker month;
- holiday availability handling passed for the `2016-02` Spring Festival month.

Warnings remain non-promotional data-shape notes:

- `top_inst` empty event dates in this batch: 1 date, `20160325`;
- `top_list` empty event dates in this batch: 0;
- non-empty ratios stayed above the 0.8 gate for every endpoint shard.

## Three-Shard Review: 2016-04 to 2016-06

This three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- post-event availability rolled correctly into the next open trading date, including the `2016-04` month-end transition to `2016-05-03`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,509;
- `top_list` duplicate stock-date-reason keys before aggregation: 12, including 8 exact duplicate rows;
- duplicate keys are a redundancy risk for later factor construction: row-level counts cannot be used directly as attention strength without stock-day aggregation, reason de-duplication, and seat-level normalization.

## Three-Shard Review: 2016-07 to 2016-09

This three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- holiday availability handling passed: `2016-09-30` rolls to the post-National-Day open date `2016-10-10`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 1 date, `20160722`;
- `top_inst` empty event dates in this batch: 0;
- endpoint non-empty ratios stayed above the 0.8 gate, with the weakest endpoint-month at 20 / 21 non-empty dates;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,121;
- `top_list` duplicate stock-date-reason keys before aggregation: 56, including 39 exact duplicate rows;
- duplicate pressure increased versus the prior batch, so direct row-count attention factors must remain blocked until stock-day aggregation, exact-duplicate suppression, reason de-duplication, and seat-level normalization are enforced in factor construction.

## Three-Shard Review: 2016-10 to 2016-12

This three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- 2016 calendar-year coverage is now complete from `2016-01` through `2016-12`;
- holiday and year-end availability handling passed: `2016-10` resumes after the National Day holiday on `2016-10-10`, and the `2016-12-30` event availability rolls to `2017-01-03`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- `top_inst` duplicate stock-date-reason keys before aggregation: 744;
- `top_list` duplicate stock-date-reason keys before aggregation: 60, including 32 exact duplicate rows;
- repeated duplicate keys across multiple months confirm that any later Dragon-Tiger attention factor must be built from the normalized stock-day aggregate rather than raw endpoint row counts.

## Three-Shard Review: 2017-01 to 2017-03

This three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- Spring Festival availability handling passed: `2017-01` rolls availability through `2017-02-03`, and `2017-02` begins at the post-holiday event date `2017-02-03`;
- Qingming holiday availability handling passed: `2017-03-31` rolls availability to `2017-04-05`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- `top_inst` duplicate stock-date-reason keys before aggregation: 647;
- `top_list` duplicate stock-date-reason keys before aggregation: 68, including 27 exact duplicate rows;
- duplicate and missing side-field warnings persist, so PIT factor construction must use lagged stock-day aggregates and cannot use raw row counts or same-day disclosure values.

## Three-Shard Review: 2017-04 to 2017-06

This three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- Qingming and month-end availability handling passed: `2017-04` starts at the post-holiday event date `2017-04-05`, and `2017-06-30` rolls availability to `2017-07-03`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- `top_inst` duplicate stock-date-reason keys before aggregation: 735;
- `top_list` duplicate stock-date-reason keys before aggregation: 62, including 41 exact duplicate rows;
- the raw endpoint duplicate pattern remains persistent enough that later factor construction must treat raw row-count strength as blocked until a normalized stock-day factor matrix is used.

## Three-Shard Review: 2017-07 to 2017-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- holiday availability handling passed: `2017-09-29` rolls availability to the post-National-Day open date `2017-10-09`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 723;
- `top_list` duplicate stock-date-reason keys before aggregation: 68, including 44 exact duplicate rows;
- raw row-count and same-day disclosure interpretations remain blocked; only lagged, de-duplicated, stock-day aggregates can feed later PIT IC.

## Three-Shard Review: 2017-10 to 2017-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- 2017 calendar-year coverage is now complete from `2017-01` through `2017-12`;
- National Day and year-end availability handling passed: `2017-10` resumes at `2017-10-09`, and `2017-12-29` rolls availability to `2018-01-02`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 666;
- `top_list` duplicate stock-date-reason keys before aggregation: 62, including 37 exact duplicate rows;
- raw endpoint row counts remain blocked as attention-strength factors; later PIT IC must use lagged stock-day aggregates with duplicate suppression, reason de-duplication, and institutional-seat normalization.

## Three-Shard Review: 2018-01 to 2018-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- Spring Festival availability handling passed for `2018-02`;
- this batch starts 2018 coverage, which is important for later regime checks because the market moved into a higher-volatility, weaker-index environment after the early-year peak.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 788;
- `top_list` duplicate stock-date-reason keys before aggregation: 149, including 38 exact duplicate rows;
- duplicate pressure rose materially in `2018-01`, so raw endpoint row-count attention factors remain blocked; only lagged, de-duplicated, stock-day aggregates can feed later PIT IC.

## Three-Shard Review: 2018-04 to 2018-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- Qingming, May holiday, Dragon Boat, and month-end availability handling passed, including `2018-04-27` rolling to `2018-05-02` and `2018-06-29` rolling to `2018-07-02`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 742;
- `top_list` duplicate stock-date-reason keys before aggregation: 62, including 38 exact duplicate rows;
- `top_list` `turnover_rate` had 1 missing row in `2018-05`;
- raw endpoint row counts and raw turnover-derived intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2018-07 to 2018-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- month-end and National Day availability handling passed, including `2018-09-28` rolling availability to `2018-10-08`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 824;
- `top_list` duplicate stock-date-reason keys before aggregation: 70, including 45 exact duplicate rows;
- raw endpoint row counts, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2018-10 to 2018-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- 2018 calendar-year coverage is now complete from `2018-01` through `2018-12`;
- National Day and year-end availability handling passed, including `2018-10-08` rolling availability to `2018-10-09` and `2018-12-28` rolling availability to `2019-01-02`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 599;
- `top_list` duplicate stock-date-reason keys before aggregation: 28, including 19 exact duplicate rows;
- `top_list` `float_values` remained sparse in this batch with 1,753 missing rows, so float-value-derived raw intensity remains blocked before PIT field-coverage guards;
- raw endpoint row counts, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2019-01 to 2019-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- Spring Festival and month-end availability handling passed, including `2019-02-01` rolling availability to `2019-02-11`, `2019-02-28` rolling to `2019-03-01`, and `2019-03-29` rolling to `2019-04-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,299;
- `top_list` duplicate stock-date-reason keys before aggregation: 878, including 49 exact duplicate rows;
- duplicate pressure rose sharply in `2019-01` and `2019-03`, so raw event count, reason count, institutional-seat count, and row-count attention signals remain blocked before PIT aggregation guards;
- raw endpoint row counts, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2019-04 to 2019-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- Qingming, Labor Day, Dragon Boat, and month-end availability handling passed, including `2019-04-30` rolling availability to `2019-05-06`, `2019-05-31` rolling to `2019-06-03`, and `2019-06-28` rolling to `2019-07-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 980;
- `top_list` duplicate stock-date-reason keys before aggregation: 1,029, including 15 exact duplicate rows;
- `top_list` `turnover_rate` had 5 missing rows across this batch, so turnover-derived raw intensity remains blocked before PIT field-coverage guards;
- duplicate pressure stayed high across all three months, so raw event count, reason count, institutional-seat count, and row-count attention signals remain blocked before PIT aggregation guards;
- raw endpoint row counts, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2019-07 to 2019-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- month-end and National Day availability handling passed, including `2019-08-30` rolling availability to `2019-09-02` and `2019-09-30` rolling availability to `2019-10-08`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,171;
- `top_list` duplicate stock-date-reason keys before aggregation: 678, including 11 exact duplicate rows;
- `top_list` `turnover_rate` had 1 missing row in `2019-08`, so turnover-derived raw intensity remains blocked before PIT field-coverage guards;
- duplicate pressure remains material, so raw event count, reason count, institutional-seat count, and row-count attention signals remain blocked before PIT aggregation guards;
- raw endpoint row counts, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2019-10 to 2019-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- five of six endpoint-month checks had a 1.0 non-empty ratio;
- `2019-12` `top_inst` had one empty event date (`20191202`) but still cleared the 0.8 non-empty-ratio gate at 0.9545;
- 2019 calendar-year coverage is now complete from `2019-01` through `2019-12`;
- National Day, month-end, and year-end availability handling passed, including `2019-10-08` rolling availability to `2019-10-09`, `2019-11-29` rolling to `2019-12-02`, and `2019-12-31` rolling to `2020-01-02`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 1, `20191202`;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,025;
- `top_list` duplicate stock-date-reason keys before aggregation: 859, including 40 exact duplicate rows;
- `top_list` had sparse raw fields in `2019-11`, including 6 missing rows each for `amount_rate`, `l_amount`, `l_buy`, `net_amount`, `net_rate`, `pct_change`, and `turnover_rate`;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2020-01 to 2020-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- 2020Q1 stress-regime coverage is now included, covering the Spring Festival extension and the COVID crash window;
- holiday and month-end availability handling passed, including `2020-01-23` rolling availability to `2020-02-03`, `2020-02-28` rolling to `2020-03-02`, and `2020-03-31` rolling to `2020-04-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,053;
- `top_list` duplicate stock-date-reason keys before aggregation: 775, including 30 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 360 rows and `l_sell` missing 42 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 6,797 missing `buy`/`buy_rate` rows and 6,784 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2020-04 to 2020-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- 2020Q2 adds the post-COVID rebound and policy-liquidity regime to the long-cycle coverage pack, so any later signal that only works here must be treated as regime-contaminated until walk-forward and regime checks prove otherwise;
- holiday and month-end availability handling passed, including `2020-04-30` rolling availability to `2020-05-06`, `2020-05-29` rolling to `2020-06-01`, and `2020-06-30` rolling to `2020-07-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,830;
- `top_list` duplicate stock-date-reason keys before aggregation: 920, including 12 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 428 rows and `l_sell` missing 18 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 6,518 missing `buy`/`buy_rate` rows and 6,506 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2020-07 to 2020-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- 2020Q3 extends the post-COVID rebound regime coverage. Any later Dragon-Tiger reversal signal concentrated in `2020-07` must be treated as regime-dependent until neutralized, walk-forward-tested, and tested outside the rebound window;
- month-end and National Day availability handling passed, including `2020-07-31` rolling availability to `2020-08-03`, `2020-08-31` rolling to `2020-09-01`, and `2020-09-30` rolling to `2020-10-09`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,691;
- `top_list` duplicate stock-date-reason keys before aggregation: 877, including 17 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 501 rows, `l_sell` missing 30 rows, `amount_rate`/`l_amount`/`l_buy`/`net_amount`/`net_rate` each missing 5 rows, and `turnover_rate` missing 2 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 7,754 missing `buy`/`buy_rate` rows and 7,587 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2020-10 to 2020-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- 2020 calendar-year coverage is now complete from `2020-01` through `2020-12`;
- National Day, month-end, and year-end availability handling passed, including `2020-10-09` rolling availability to `2020-10-12`, `2020-10-30` rolling to `2020-11-02`, `2020-11-30` rolling to `2020-12-01`, and `2020-12-31` rolling to `2021-01-04`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,807;
- `top_list` duplicate stock-date-reason keys before aggregation: 554, including 52 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 269 rows, `l_sell` missing 75 rows, and `l_buy` missing 6 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 5,112 missing `buy`/`buy_rate` rows and 5,150 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2021-01 to 2021-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- five of six endpoint-month checks had a 1.0 non-empty ratio;
- `2021-03` `top_inst` had one empty event date (`20210322`) but still cleared the 0.8 non-empty-ratio gate at 0.9565;
- New Year, Spring Festival, and month-end availability handling passed, including `2021-01-04` rolling availability to `2021-01-05`, `2021-01-29` rolling to `2021-02-01`, `2021-02-26` rolling to `2021-03-01`, and `2021-03-31` rolling to `2021-04-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 1, `20210322`;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,568;
- `top_list` duplicate stock-date-reason keys before aggregation: 927, including 22 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 512 rows, `l_sell` missing 66 rows, and `amount_rate`/`l_amount`/`l_buy`/`net_amount`/`net_rate` each missing 33 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 6,820 missing `buy`/`buy_rate` rows and 6,933 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2021-04 to 2021-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- Qingming, May Day, Dragon Boat, and month-end availability handling passed, including `2021-04-01` rolling to `2021-04-02`, `2021-04-30` rolling to `2021-05-06`, `2021-05-31` rolling to `2021-06-01`, and `2021-06-30` rolling to `2021-07-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,139;
- `top_list` duplicate stock-date-reason keys before aggregation: 659, including 23 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 356 rows, `l_sell` missing 42 rows, and `amount_rate`/`l_amount`/`l_buy`/`net_amount`/`net_rate` each missing 1 row across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 7,768 missing `buy`/`buy_rate` rows and 7,743 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2021-07 to 2021-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- five of six endpoint-month checks had a 1.0 non-empty ratio;
- `2021-08` `top_list` had one empty event date (`20210811`) but still cleared the 0.8 non-empty-ratio gate at 0.9545;
- month-end, summer, Mid-Autumn Festival, and National Day boundary availability handling passed, including `2021-07-30` rolling to `2021-08-02`, `2021-08-31` rolling to `2021-09-01`, `2021-09-30` rolling to `2021-10-08`, and all aggregate rows keeping `available_date` strictly after `trade_date`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 1, `20210811`;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 4,065;
- `top_list` duplicate stock-date-reason keys before aggregation: 567, including 50 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 295 rows, `l_sell` missing 116 rows, `amount_rate`/`l_amount`/`l_buy`/`net_amount`/`net_rate` each missing 100 rows, and `turnover_rate` missing 27 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 7,459 missing `buy`/`buy_rate` rows and 7,382 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2021-10 to 2021-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- National Day, month-end, and year-end availability handling passed, including `2021-10-08` rolling to `2021-10-11`, `2021-10-29` rolling to `2021-11-01`, `2021-11-30` rolling to `2021-12-01`, and `2021-12-31` rolling to `2022-01-04`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,530;
- `top_list` duplicate stock-date-reason keys before aggregation: 498, including 10 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 204 rows, `l_sell` missing 26 rows, `turnover_rate` missing 83 rows, and `close`/`pct_change` each missing 51 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 8,232 missing `buy`/`buy_rate` rows and 8,245 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2022-01 to 2022-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- New Year, Spring Festival, month-end, and early 2022 drawdown-regime coverage handling passed, including `2022-01-04` rolling to `2022-01-05`, `2022-01-28` rolling to `2022-02-07`, `2022-02-28` rolling to `2022-03-01`, and `2022-03-31` rolling to `2022-04-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,436;
- `top_list` duplicate stock-date-reason keys before aggregation: 551, including 4 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 298 rows and `l_sell` missing 8 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 8,399 missing `buy`/`buy_rate` rows and 8,329 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2022-04 to 2022-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- five of six endpoint-month checks had a 1.0 non-empty ratio;
- `2022-04` `top_inst` had one empty event date (`20220426`) but still cleared the 0.8 non-empty-ratio gate at 0.9474;
- Qingming, May Day, Dragon Boat, month-end, and 2022 drawdown/rebound-regime coverage handling passed, including `2022-04-01` rolling to `2022-04-06`, `2022-04-29` rolling to `2022-05-05`, `2022-05-31` rolling to `2022-06-01`, and `2022-06-30` rolling to `2022-07-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 1, `20220426`;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,717;
- `top_list` duplicate stock-date-reason keys before aggregation: 620, including 7 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 311 rows, `l_sell` missing 19 rows, `l_buy` missing 11 rows, and `amount_rate`/`l_amount`/`net_amount`/`net_rate` each missing 7 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 10,312 missing `buy`/`buy_rate` rows and 10,609 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2022-07 to 2022-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- summer drawdown/rebound, month-end, and National Day pre-holiday availability handling passed, including `2022-07-29` rolling to `2022-08-01`, `2022-08-31` rolling to `2022-09-01`, and `2022-09-30` rolling to `2022-10-10`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,264;
- `top_list` duplicate stock-date-reason keys before aggregation: 354, including 13 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 65 rows, `turnover_rate` missing 35 rows, `l_sell` missing 16 rows, and `l_buy` missing 3 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 7,971 missing `buy`/`buy_rate` rows and 7,952 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2022-10 to 2022-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- National Day, month-end, and year-end availability handling passed, including `2022-10-10` rolling to `2022-10-11`, `2022-10-31` rolling to `2022-11-01`, `2022-11-30` rolling to `2022-12-01`, and `2022-12-30` rolling to `2023-01-03`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,209;
- `top_list` duplicate stock-date-reason keys before aggregation: 258, including 10 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 87 rows, `turnover_rate` missing 81 rows, and `l_sell` missing 14 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 6,326 missing `buy`/`buy_rate` rows and 6,325 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2023-01 to 2023-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- Spring Festival, month-end, and Q1 availability handling passed, including `2023-01-03` rolling to `2023-01-04`, `2023-01-31` rolling to `2023-02-01`, `2023-02-28` rolling to `2023-03-01`, and `2023-03-31` rolling to `2023-04-03`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,776;
- `top_list` duplicate stock-date-reason keys before aggregation: 270, including 0 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 53 rows, `turnover_rate` missing 53 rows, and `l_sell` missing 2 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 5,398 missing `buy`/`buy_rate` rows and 5,342 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2023-04 to 2023-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- Qingming, May Day, Dragon Boat, month-end, and Q2 availability handling passed, including `2023-04-03` rolling to `2023-04-04`, `2023-04-28` rolling to `2023-05-04`, `2023-05-31` rolling to `2023-06-01`, and `2023-06-30` rolling to `2023-07-03`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 3,374;
- `top_list` duplicate stock-date-reason keys before aggregation: 389, including 10 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 95 rows, `turnover_rate` missing 95 rows, `l_sell` missing 14 rows, and `l_buy` missing 3 rows across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 8,457 missing `buy`/`buy_rate` rows and 8,468 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2023-07 to 2023-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks had a 1.0 non-empty ratio;
- summer regime, month-end, and National Day pre-holiday availability handling passed, including `2023-07-31` rolling to `2023-08-01`, `2023-08-31` rolling to `2023-09-01`, and `2023-09-28` rolling to `2023-10-09`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 4,011;
- `top_list` duplicate stock-date-reason keys before aggregation: 400, including 11 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 137 rows, `turnover_rate` missing 137 rows, `l_sell` missing 17 rows, `l_buy` missing 3 rows, and `amount_rate`/`l_amount`/`net_amount`/`net_rate` each missing 1 row across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 7,466 missing `buy`/`buy_rate` rows and 7,471 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2023-10 to 2023-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- National Day, month-end, and year-end availability handling passed, including `2023-10-09` rolling to `2023-10-10`, `2023-10-31` rolling to `2023-11-01`, `2023-11-30` rolling to `2023-12-01`, and `2023-12-29` rolling to `2024-01-02`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 1 date, `20231025`;
- `top_inst` empty event dates in this batch: 1 date, `20231030`;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,470;
- `top_list` duplicate stock-date-reason keys before aggregation: 282, including 4 exact duplicate rows;
- `top_list` sparse fields remain material: `float_values` missing 98 rows, `turnover_rate` missing 98 rows, `l_sell` missing 7 rows, `l_buy` missing 1 row, and `amount_rate`/`l_amount`/`net_amount`/`net_rate`/`close`/`pct_change` each missing 1 row across the batch;
- `top_inst` buy/sell side fields remain sparse by construction, with 7,816 missing `buy`/`buy_rate` rows and 7,824 missing `sell`/`sell_rate` rows across the batch;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, missing price fields, and missing-side buy/sell intensity remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2024-01 to 2024-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- New Year, Spring Festival, February month-end, and March month-end availability handling passed, including `2024-01-31` rolling to `2024-02-01`, `2024-02-29` rolling to `2024-03-01`, and `2024-03-29` rolling to `2024-04-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 4,041;
- `top_list` duplicate stock-date-reason keys before aggregation: 414, including 7 exact duplicate rows;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and calendar-short-month crowding remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2024-04 to 2024-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- Tomb-Sweeping and Labor Day holidays, May month-end, Dragon Boat holiday, and June month-end availability handling passed, including `2024-04-30` rolling to `2024-05-06`, `2024-05-31` rolling to `2024-06-03`, and `2024-06-28` rolling to `2024-07-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 3,187;
- `top_list` duplicate stock-date-reason keys before aggregation: 404, including 1 exact duplicate row;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and holiday-short-month crowding remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2024-07 to 2024-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- July month-end, August month-end, and National Day holiday availability handling passed, including `2024-07-31` rolling to `2024-08-01`, `2024-08-30` rolling to `2024-09-02`, and `2024-09-30` rolling to `2024-10-08`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 1,588;
- `top_list` duplicate stock-date-reason keys before aggregation: 66, including 13 exact duplicate rows;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and pre-holiday crowding remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2024-10 to 2024-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- National Day recovery, November month-end, year-end, and New Year availability handling passed, including `2024-10-31` rolling to `2024-11-01`, `2024-11-29` rolling to `2024-12-02`, and `2024-12-31` rolling to `2025-01-02`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,648;
- `top_list` duplicate stock-date-reason keys before aggregation: 22, including 7 exact duplicate rows;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and year-end crowding remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2025-01 to 2025-03

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- New Year, Spring Festival, February month-end, and March month-end availability handling passed, including `2025-01-27` rolling to `2025-02-05`, `2025-02-28` rolling to `2025-03-03`, and `2025-03-31` rolling to `2025-04-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 2,398;
- `top_list` duplicate stock-date-reason keys before aggregation: 2, including 2 exact duplicate rows;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and holiday-short-month crowding remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2025-04 to 2025-06

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- Tomb-Sweeping, Labor Day, Dragon Boat, and June month-end availability handling passed, including `2025-04-30` rolling to `2025-05-06`, `2025-05-30` rolling to `2025-06-03`, and `2025-06-30` rolling to `2025-07-01`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 3 dates, `20250411`, `20250421`, and `20250423`;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 3,267;
- `top_list` duplicate stock-date-reason keys before aggregation: 0, including 0 exact duplicate rows;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and sparse `top_list` event days remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2025-07 to 2025-09

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- July month-end, August month-end, and National Day pre-holiday availability handling passed, including `2025-07-31` rolling to `2025-08-01`, `2025-08-29` rolling to `2025-09-01`, and `2025-09-30` rolling to `2025-10-09`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 4,042;
- `top_list` duplicate stock-date-reason keys before aggregation: 7, including 7 exact duplicate rows;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and pre-holiday crowding remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Three-Shard Review: 2025-10 to 2025-12

The latest three-shard batch passed the coverage gate:

- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0;
- blockers: 0;
- all six endpoint-month checks stayed above the 0.8 non-empty-ratio gate;
- National Day recovery, November month-end, year-end, and 2026 New Year availability handling passed, including `2025-10-31` rolling to `2025-11-03`, `2025-11-28` rolling to `2025-12-01`, and `2025-12-31` rolling to `2026-01-05`.

Warnings remain non-promotional data-shape notes:

- `top_list` empty event dates in this batch: 0;
- `top_inst` empty event dates in this batch: 0;
- `top_inst` duplicate stock-date-reason keys before aggregation: 5,120;
- `top_list` duplicate stock-date-reason keys before aggregation: 6, including 6 exact duplicate rows;
- stock-day aggregate missing-value count maps were empty in this batch, so no positive missing counts were emitted for PIT aggregate fields;
- `top_inst` missing-value count maps were empty in this batch, so no positive missing buy/sell-side counts were emitted;
- raw endpoint row counts, turnover-derived intensity, institutional-seat counts, duplicate raw keys, and year-end crowding remain blocked as factor inputs until stock-day aggregation, duplicate suppression, reason de-duplication, institutional-seat normalization, and field-coverage guards are enforced in PIT factor construction.

## Current Evidence

Current completed shard coverage:

- completed months: 132;
- completed trade dates: 2,674;
- `top_list` rows: 184,592;
- `top_inst` rows: 2,228,702;
- stock-day aggregate rows: 159,675;
- request errors: 0;
- missing `available_date`: 0;
- available-date lag violations: 0.

## PIT IC Prescreen Result - 2026-06-25

The first long-cycle PIT event IC prescreen has now run on the completed Dragon-Tiger stock-day aggregate:

- command output directory: `data/reports/round232_dragon_tiger_pit_ic_prescreen_20260625`;
- analysis window: 2015-01-01 through 2025-12-31;
- signal date rule: `available_date` strictly after Dragon-Tiger trade date;
- horizon: 1 trading day, matching the pre-registered `_1d` candidate family;
- candidates tested: 5;
- factor rows: 777,349;
- aligned rows: 742,130;
- FDR-significant tests: 5;
- direct research leads: 0;
- style residual repair candidates: 2.

Top two repair candidates:

- `dragon_tiger_net_buy_continuation_1d`: IC 0.0962, ICIR 0.494, t-stat 25.47, industry-neutral RankIC 0.2828, size-neutral RankIC 0.0243, size-neutral retention 0.252.
- `dragon_tiger_institutional_net_buy_pressure_1d`: IC 0.0962, ICIR 0.497, t-stat 25.61, industry-neutral RankIC 0.2896, size-neutral RankIC 0.0244, size-neutral retention 0.254.

Interpretation:

- These are not promotion-ready factors.
- The raw and industry-neutral signals are strong, but both are heavily size/style contaminated.
- Portfolio grids remain blocked.
- The immediate next step was size/liquidity/style residual repair, not same-family parameter expansion or direct portfolio conversion.

Next direction:

```text
round233_dragon_tiger_size_residual_repair_before_portfolio_grid_preflight
```

## Size Residual Repair Result - 2026-06-25

Round233 residual repair has now run:

- command output directory: `data/reports/round233_dragon_tiger_size_residual_repair_20260625`;
- source factor rows: 310,858;
- residual factor rows: 290,792;
- aligned rows: 289,846;
- candidates tested: 2;
- neutral-gate pass tests: 2;
- research leads: 0;
- promotion allowed candidates: 0.

The repair removed much of the size contamination, but both candidates still fail the research-lead gate because ICIR remains below 0.30 and quantile monotonicity is weak at 0.40.

## Decision

The full 2015-2025 long-cycle Dragon-Tiger coverage gate is complete, the first 1-day PIT event IC prescreen has run, and the Round233 size residual repair has also run. Portfolio grids, walk-forward promotion, and profitability claims remain blocked because residual repair produced zero research leads.

Next direction:

```text
round234_hibernate_or_rotate_dragon_tiger_after_size_residual_repair_failure
```

Only after a new orthogonal Dragon-Tiger hypothesis or a different family clears candidate-gate review, duplicate/exposure controls, walk-forward, cost/capacity, regime, and final-holdout gates should the workflow advance to:

```text
round232_dragon_tiger_portfolio_grid_preflight
```

## Non-Claims

- No alpha has been promoted in this report.
- No Sharpe, annual return, profit rate, win rate, or RankIC result is claimed.
- No portfolio grid is allowed.
- No promotion is allowed.
- No final holdout has been touched.
