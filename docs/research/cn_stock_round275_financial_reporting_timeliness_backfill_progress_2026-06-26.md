# CN Stock Round275 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-round275-financial-timeliness-20260626
- Scope: CN A-share stock factor mining
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Purpose

Round275 completed the remaining two subsegments of shard 9 for the financial reporting timeliness source-coverage path. No factor candidate was generated.

The route remains source construction. Financial reporting timeliness candidate generation is still blocked until aggregate PIT financial statement coverage is broad enough for robust cross-sectional mining.

## Startup Gate

- Startup gate: cleared.
- Required direction: `round275_continue_financial_reporting_timeliness_backfill_until_1000_symbols_or_rotate`.
- Candidate generation: blocked until the aggregate source gate clears.
- IC screens, portfolio grids, promotion, and final holdout access: blocked.

## Backfill Evidence

Two non-overlapping shard 9 segments were completed with request throttling:

| Segment | Symbols | Endpoint requests | Processed rows | Empty requests | Duplicate rows | Readiness |
|---|---:|---:|---:|---:|---:|---|
| shard 9 offset 10 limit 5 | 5 | 660 | 215 | 23 | 2 | passed |
| shard 9 offset 15 limit 5 | 5 | 660 | 220 | 0 | 0 | passed |
| total | 10 | 1,320 | 435 | 23 | 2 | passed |

Selected symbols:

- offset 10: `002320.SZ`, `000572.SZ`, `300825.SZ`, `000559.SZ`, `002069.SZ`
- offset 15: `000582.SZ`, `000539.SZ`, `600740.SH`, `000571.SZ`, `000825.SZ`

Both segments passed the required PIT column groups:

- `accounting_accrual_quality`: `netprofit`, `n_cashflow_act`, `total_assets`
- `asset_growth_quality`: `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab`

## Source Audit

Final Round275 aggregate audit:

- Output: `data/reports/round275_financial_reporting_timeliness_source_audit_after_shard9_complete_20260626`
- Status: blocked
- Sources scanned: 69
- Aggregate rows: 48,117
- Aggregate unique symbols: 231
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
| after Round275 shard 9 completion | 48,117 | 231 | false |

Round275 added 10 fetched symbols and increased aggregate unique-symbol coverage by 10. Shard 9 is now complete. Coverage is still only 23.1% of the 1,000-symbol source gate.

## Risk Notes

Round275 offset 10 had 23 empty endpoint requests and 2 duplicate rows. This did not break readiness or required field coverage, but it is a new data-quality watch item after several clean zero-empty subsegments. If empty requests become repeated across future subshards, the route should pause for endpoint-level audit rather than blindly continuing.

## Decision

Continue the backfill route. Do not generate financial reporting timeliness factors yet.

This direction remains viable because:

- both new subsegments passed readiness;
- aggregate symbol coverage increased by 10;
- shard 9 is complete;
- required PIT fields remain present.

This direction remains blocked because:

- 231 symbols is far below the 1,000-symbol minimum;
- a 231-symbol sample can still create fragile cross-sectional IC and false positives;
- no IC, portfolio, promotion, or final-holdout claim is allowed from this coverage level.

## Next Action

Round276 should continue from shard 10:

```text
shard_id=10, symbol_offset=0, symbol_limit=5
```

Expected next symbols:

```text
000546.SZ, 002080.SZ, 000534.SZ, 600050.SH, 002175.SZ
```

Use the same throttled command shape:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 10 --symbol-offset 0 --symbol-limit 5 --max-endpoint-requests 700 --adapter-max-retries 6 --adapter-retry-sleep-seconds 20 --adapter-request-sleep-seconds 0.36 --output-dir data\processed\round276_financial_statement_shard10_offset0_limit5_20260626
```

Continue blocking candidate preregistration, IC screens, portfolio grids, promotion, and final holdout access until aggregate coverage clears the source gate.
