# Round95 Fina Indicator Shard1 Full100 Backfill Design

## Objective

Run shard 1 from the Round93 `fina_indicator` symbol-universe plan across the full 2015-2025 quarterly period range for 100 CN A-share stock symbols.

This is a data-quality and PIT-readiness round. It is not a profitability-factor mining round and does not make Sharpe, profit, or win-rate claims.

## Guardrails

- Use CN A-share stock scope only.
- Use the Round93 shard plan as the source of symbols.
- Select shard 1 with 100 symbols.
- Expected requests: `100 symbols * 44 quarters = 4,400`.
- Record empty responses instead of aborting.
- PIT readiness must pass after the backfill.
- Duplicate financial keys must remain 0.
- Missing asset ids must remain 0.
- Do not promote, paper-ready, or live-enable any factor from this single shard.

## Acceptance Criteria

- `shard_backfill_smoke.json` is written.
- `limited_backfill_smoke.json` is written.
- `tushare_financial_pit_readiness.json` is written.
- All 4,400 raw request partitions are present.
- Processed rows are non-zero.
- `duplicate_rows == 0`.
- `missing_asset_id_rows == 0`.
- PIT readiness passes.
- Startup gate advances only to profitability-quality candidate pre-registration and coverage audit, not to promotion.

## Non-Goals

- No factor backtest.
- No Sharpe/profit/win-rate ranking.
- No full-universe backfill.
- No GitHub push.
- No broker, account, order, or live-trading action.
