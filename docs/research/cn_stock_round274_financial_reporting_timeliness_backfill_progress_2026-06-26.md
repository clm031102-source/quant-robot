# CN Stock Round274 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-round274-financial-timeliness-20260626
- Scope: CN A-share stock factor mining
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Purpose

Round274 continued the financial reporting timeliness source-coverage path. It extended shard 9 with two non-overlapping subsegments. No factor candidate was generated.

This is intentional. The current route is still source construction, not alpha discovery. Candidate generation remains blocked until aggregate PIT financial statement coverage is broad enough to support robust cross-sectional mining.

## Startup Gate

- Startup gate: cleared.
- Required direction: `round274_continue_financial_reporting_timeliness_backfill_until_1000_symbols_or_rotate`.
- Candidate generation: blocked until the aggregate source gate clears.
- IC screens, portfolio grids, promotion, and final holdout access: blocked.

## Backfill Evidence

Two non-overlapping shard 9 segments were completed with request throttling:

| Segment | Symbols | Endpoint requests | Processed rows | Empty requests | Readiness |
|---|---:|---:|---:|---:|---|
| shard 9 offset 0 limit 5 | 5 | 660 | 220 | 0 | passed |
| shard 9 offset 5 limit 5 | 5 | 660 | 220 | 0 | passed |
| total | 10 | 1,320 | 440 | 0 | passed |

Selected symbols:

- offset 0: `000026.SZ`, `600897.SH`, `000837.SZ`, `000777.SZ`, `000663.SZ`
- offset 5: `002054.SZ`, `002224.SZ`, `000722.SZ`, `000605.SZ`, `000672.SZ`

Both segments passed the required PIT column groups:

- `accounting_accrual_quality`: `netprofit`, `n_cashflow_act`, `total_assets`
- `asset_growth_quality`: `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab`

## Source Audit

Final Round274 aggregate audit:

- Output: `data/reports/round274_financial_reporting_timeliness_source_audit_after_shard9_offset5_20260626`
- Status: blocked
- Sources scanned: 67
- Aggregate rows: 45,924
- Aggregate unique symbols: 221
- Minimum required symbols: 1,000
- Required end-year coverage: 8
- Candidate plan allowed: false
- Blocker: `unique_symbol_count_below_minimum`

Progress:

| Checkpoint | Aggregate rows | Aggregate unique symbols | Candidate plan allowed |
|---|---:|---:|---|
| after Round271 shard 7 completion | 39,265 | 195 | false |
| after Round272 shard 8 offset 0/5 | 41,494 | 203 | false |
| after Round273 shard 8 completion | 43,710 | 212 | false |
| after Round274 shard 9 offset 0/5 | 45,924 | 221 | false |

Round274 added 10 fetched symbols and increased aggregate unique-symbol coverage by 9. The backfill channel remains productive, but coverage is still only 22.1% of the 1,000-symbol source gate.

## Decision

Continue the backfill route. Do not generate financial reporting timeliness factors yet.

This direction remains viable because:

- both new subsegments passed readiness;
- empty requests remained at zero;
- live Tushare throttling still worked under 660 requests per subsegment;
- required PIT fields remain present;
- aggregate symbol coverage continued to increase.

This direction remains blocked because:

- 221 symbols is far below the 1,000-symbol minimum;
- a 221-symbol sample can still create fragile cross-sectional IC and false positives;
- no IC, portfolio, promotion, or final-holdout claim is allowed from this coverage level.

## Next Action

Round275 should continue from shard 9:

```text
shard_id=9, symbol_offset=10, symbol_limit=5
```

Expected next symbols:

```text
002320.SZ, 000572.SZ, 300825.SZ, 000559.SZ, 002069.SZ
```

Use the same throttled command shape:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 9 --symbol-offset 10 --symbol-limit 5 --max-endpoint-requests 700 --adapter-max-retries 6 --adapter-retry-sleep-seconds 20 --adapter-request-sleep-seconds 0.36 --output-dir data\processed\round275_financial_statement_shard9_offset10_limit5_20260626
```

Continue blocking candidate preregistration, IC screens, portfolio grids, promotion, and final holdout access until aggregate coverage clears the source gate.
