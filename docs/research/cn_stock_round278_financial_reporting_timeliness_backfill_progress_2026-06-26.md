# CN Stock Round278 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-round278-financial-timeliness-20260626`
- Scope: CN A-share stock financial reporting timeliness source construction
- Safety: research-to-review only. No broker connection, account reads, order placement, or live trading.

## Startup Gate

Round278 startup gates cleared for source construction:

- Quant PM startup gate: ready, no blockers
- CN stock startup gate: cleared, no blockers
- CN data manifest: review_required with no blockers
- Manifest warnings: extreme return rows are present; moneyflow symbol coverage remains below bar coverage
- last completed round before execution: 277
- next round before execution: 278
- required source gate: 1,000 unique symbols before financial reporting timeliness factor candidate generation
- final holdout: blocked

This round continued source construction only. It did not generate, screen, or promote any factor.

## Backfill Work

Round278 completed the first half of shard 11:

| Segment | Symbols | Endpoint Requests | Processed Rows | Empty Requests | Duplicate Rows | Readiness |
|---|---:|---:|---:|---:|---:|---|
| shard11 offset0 limit5 | 5 | 660 | 220 | 0 | 0 | passed |
| shard11 offset5 limit5 | 5 | 660 | 203 | 53 | 0 | passed |
| total | 10 | 1,320 | 423 | 53 | 0 | passed |

Symbols fetched:

```text
300065.SZ, 002081.SZ, 000712.SZ, 002251.SZ, 000755.SZ,
000503.SZ, 300997.SZ, 002444.SZ, 000039.SZ, 000561.SZ
```

Both subsegments passed required PIT statement readiness:

- required column groups passing: 2 / 2
- readiness blockers: none
- ann date range across the two subsegments: 2015-04-22 through 2026-04-29
- report period range across the two subsegments: 2015-03-31 through 2025-12-31

## Empty Request Root Cause

Round278 found a more precise reason for the empty-request spike:

| Breakdown | Count |
|---|---:|
| total empty requests | 53 |
| `300997.SZ` empty requests | 53 |
| `balancesheet` empty requests | 19 |
| `income` empty requests | 17 |
| `cashflow` empty requests | 17 |
| 2015 empty requests | 12 |
| 2016 empty requests | 12 |
| 2017 empty requests | 9 |
| 2018 empty requests | 9 |
| 2019 empty requests | 9 |
| 2020 empty requests | 2 |

Local `stock_basic` metadata shows:

```text
300997.SZ list_date = 2021-06-02
```

Interpretation: the Round278 empty requests are not random Tushare instability. They are overwhelmingly pre-listing or early no-report statement requests for a stock that listed in 2021. The process risk is therefore a request-planning issue.

## Reusable Process Optimization

The shard backfill CLI now supports a reusable stock-basic list-date filter:

```powershell
python scripts\run_financial_statement_shard_backfill.py `
  --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json `
  --shard-id 11 `
  --symbol-offset 10 `
  --symbol-limit 5 `
  --stock-basic-path data\processed\cn_stock_metadata\metadata\tushare_stock_basic `
  --max-endpoint-requests 700 `
  --output-dir data\processed\<round-output>
```

The CLI records:

- planned symbol-period count
- active symbol-period count
- pre-listing skipped symbol-period count
- pre-listing skipped endpoint request count
- exact skipped `symbol:period:before_list_date` entries

Unit coverage was added for `300997.SZ` with a 2021-06-02 list date. The test verifies that pre-listing 2020-12-31 and 2021-03-31 requests are skipped while 2021-06-30 remains active.

## Aggregate Source Audit

After adding Round278 shard11 offset0 and offset5 processed roots, the aggregate source audit reported:

| Metric | Value |
|---|---:|
| Sources | 75 |
| Aggregate rows | 54,667 |
| Aggregate unique symbols | 257 |
| Minimum required unique symbols | 1,000 |
| Source-ready count | 0 |
| Candidate plan allowed | false |

The blocker remains:

```text
unique_symbol_count_below_minimum
```

Coverage increased from 249 after Round277 to 257 after Round278. The 10 fetched symbols produced 8 incremental unique symbols in the aggregate union.

## Factor Outcome

Round278 produced:

- new factor names: 0
- research leads: 0
- paper-ready candidates: 0
- promotable candidates: 0
- live/manual signals: 0

This is intentional. The source gate still blocks factor generation before 1,000 unique symbols. Running IC screens, portfolio grids, or promotion checks at 257 symbols would repeat a known short-sample overfitting failure mode.

## Direction Decision

Continue financial reporting timeliness source construction, but change the operating procedure.

Reasons to continue:

- aggregate coverage increased;
- both Round278 subsegments passed readiness;
- the empty-request spike now has a concrete, fixable root cause;
- the route still has not reached fair alpha-testing conditions.

Required change:

- Round279 must use `--stock-basic-path` to filter pre-listing financial statement periods.
- Empty-request monitoring must distinguish true post-listing endpoint gaps from pre-listing request waste.
- Candidate factor generation remains blocked until aggregate source coverage reaches the 1,000-symbol gate.

Round279 should continue shard 11:

```text
shard_id=11, symbol_offset=10, symbol_limit=5
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
- no blind continuation without stock-basic pre-listing filtering.
