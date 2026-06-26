# CN Stock Round272 Financial Reporting Timeliness Backfill Progress

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-round272-financial-timeliness-20260626
- Scope: CN A-share stock factor mining
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Purpose

Round272 continued the financial reporting timeliness data-foundation path selected after Round270 and Round271. It did not generate factor candidates. The source gate still requires broad point-in-time financial reporting coverage before any IC screen, portfolio grid, or promotion claim.

## Startup Gate

- Startup gate: cleared.
- Required direction: `round272_continue_financial_reporting_timeliness_backfill_until_1000_symbols_or_rotate`.
- Candidate generation: blocked until aggregate source coverage reaches the gate.
- Portfolio grid, promotion, final holdout access: blocked.

## Backfill Evidence

Two non-overlapping shard 8 segments were completed with request throttling:

| Segment | Symbols | Endpoint requests | Processed rows | Empty requests | Readiness |
|---|---:|---:|---:|---:|---|
| shard 8 offset 0 limit 5 | 5 | 660 | 245 | 0 | passed |
| shard 8 offset 5 limit 5 | 5 | 660 | 220 | 0 | passed |
| total | 10 | 1,320 | 465 | 0 | passed |

Selected symbols:

- offset 0: `000752.SZ`, `600639.SH`, `000920.SZ`, `000563.SZ`, `002084.SZ`
- offset 5: `000521.SZ`, `000633.SZ`, `000425.SZ`, `000659.SZ`, `000010.SZ`

Both segments passed the required PIT column groups:

- `accounting_accrual_quality`: `netprofit`, `n_cashflow_act`, `total_assets`
- `asset_growth_quality`: `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab`

## Source Audit

Final Round272 aggregate audit:

- Output: `data/reports/round272_financial_reporting_timeliness_source_audit_after_shard8_offset5_20260626`
- Status: blocked
- Sources scanned: 63
- Aggregate rows: 41,494
- Aggregate unique symbols: 203
- Minimum required symbols: 1,000
- End-year count: 11
- Required fields present: yes
- Candidate plan allowed: false
- Blocker: `unique_symbol_count_below_minimum`

Progress versus Round271:

| Checkpoint | Aggregate rows | Aggregate unique symbols | Candidate plan allowed |
|---|---:|---:|---|
| after Round271 shard 7 completion | 39,265 | 195 | false |
| after Round272 shard 8 offset 0 | 40,390 | 200 | false |
| after Round272 shard 8 offset 5 | 41,494 | 203 | false |

Round272 added 10 fetched symbols, while aggregate unique-symbol coverage increased by 8 because part of the new shard overlapped symbols already present in earlier financial PIT sources.

## Decision

Continue the backfill route, but keep financial reporting timeliness factor generation blocked.

This direction remains worth continuing because:

- live Tushare statement calls completed under throttling;
- both new subshards passed readiness;
- empty requests remained at zero;
- long-cycle end-year coverage and required fields remain adequate.

This direction is still not allowed to mine candidates because:

- 203 symbols is only 20.3% of the 1,000-symbol source gate;
- a 203-symbol source can easily create fragile cross-sectional IC;
- no result from this coverage level can support portfolio or promotion claims.

## Next Action

Round273 should continue from the next non-overlapping subshard:

```text
shard_id=8, symbol_offset=10, symbol_limit=5
```

Expected next symbols:

```text
000802.SZ, 000560.SZ, 002758.SZ, 000913.SZ, 002093.SZ
```

Use the same throttled command shape:

```powershell
python scripts\run_financial_statement_shard_backfill.py --plan-json data\reports\round236_financial_statement_symbol_shard_plan_20260625\financial_statement_symbol_shard_plan.json --shard-id 8 --symbol-offset 10 --symbol-limit 5 --max-endpoint-requests 700 --adapter-max-retries 6 --adapter-retry-sleep-seconds 20 --adapter-request-sleep-seconds 0.36 --output-dir data\processed\round273_financial_statement_shard8_offset10_limit5_20260626
```

Continue blocking candidate preregistration, IC screens, portfolio grids, promotion, and final holdout access until aggregate coverage clears the source gate.

