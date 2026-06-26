# CN Stock Round273 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-round273-financial-timeliness-20260626
- Scope: CN A-share stock factor mining
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Purpose

Round273 continued the source-coverage path required before financial reporting timeliness factors can be mined. It completed the remaining two subsegments of shard 8. No factor candidate was generated.

## Startup Gate

- Startup gate: cleared.
- Required direction: `round273_continue_financial_reporting_timeliness_backfill_until_1000_symbols_or_rotate`.
- Candidate generation: blocked until the aggregate source gate clears.
- Portfolio grid, promotion, and final holdout access: blocked.

## Backfill Evidence

Two non-overlapping shard 8 segments were completed with request throttling:

| Segment | Symbols | Endpoint requests | Processed rows | Empty requests | Readiness |
|---|---:|---:|---:|---:|---|
| shard 8 offset 10 limit 5 | 5 | 660 | 220 | 0 | passed |
| shard 8 offset 15 limit 5 | 5 | 660 | 220 | 0 | passed |
| total | 10 | 1,320 | 440 | 0 | passed |

Selected symbols:

- offset 10: `000802.SZ`, `000560.SZ`, `002758.SZ`, `000913.SZ`, `002093.SZ`
- offset 15: `000537.SZ`, `000430.SZ`, `000610.SZ`, `002637.SZ`, `000709.SZ`

Both segments passed the required PIT column groups:

- `accounting_accrual_quality`: `netprofit`, `n_cashflow_act`, `total_assets`
- `asset_growth_quality`: `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab`

## Source Audit

Final Round273 aggregate audit:

- Output: `data/reports/round273_financial_reporting_timeliness_source_audit_after_shard8_complete_20260626`
- Status: blocked
- Sources scanned: 65
- Aggregate rows: 43,710
- Aggregate unique symbols: 212
- Minimum required symbols: 1,000
- End-year count: 11
- Required fields present: yes
- Candidate plan allowed: false
- Blocker: `unique_symbol_count_below_minimum`

Progress:

| Checkpoint | Aggregate rows | Aggregate unique symbols | Candidate plan allowed |
|---|---:|---:|---|
| after Round271 shard 7 completion | 39,265 | 195 | false |
| after Round272 shard 8 offset 0/5 | 41,494 | 203 | false |
| after Round273 shard 8 completion | 43,710 | 212 | false |

Round273 added 10 fetched symbols and increased aggregate unique-symbol coverage by 9. Shard 8 is now complete.

## Decision

Continue the backfill route. Do not generate financial reporting timeliness factors yet.

This direction remains viable because:

- both new subsegments passed readiness;
- empty requests remained at zero;
- live Tushare throttling still worked;
- aggregate end-year coverage remains 11 years;
- required PIT fields remain present.

This direction remains blocked because:

- 212 symbols is only 21.2% of the 1,000-symbol source gate;
- a 212-symbol sample is not enough for robust cross-sectional factor mining;
- no IC, portfolio, promotion, or final-holdout claim is allowed from this coverage level.

## Next Action

Round274 should continue from shard 9:

```text
shard_id=9, symbol_offset=0, symbol_limit=5
```

Expected next symbols:

```text
000026.SZ, 600897.SH, 000837.SZ, 000777.SZ, 000663.SZ
```

Use the same throttled command shape:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 9 --symbol-offset 0 --symbol-limit 5 --max-endpoint-requests 700 --adapter-max-retries 6 --adapter-retry-sleep-seconds 20 --adapter-request-sleep-seconds 0.36 --output-dir data\processed\round274_financial_statement_shard9_offset0_limit5_20260626
```

Continue blocking candidate preregistration, IC screens, portfolio grids, promotion, and final holdout access until aggregate coverage clears the source gate.
