# Round94 Fina Indicator First10 Shard Smoke Design

## Objective

Run the first 10 symbols from Round93 shard 1 across the full 2015-2025 quarterly `fina_indicator` period range before attempting any full 100-symbol shard.

This is a data-quality and runtime smoke, not a factor-mining or promotion round.

## Guardrails

- Use CN A-share stock scope only.
- Use the Round93 shard plan as the source of symbols.
- Select shard 1 and the first 10 symbols only.
- Expected requests: `10 symbols * 44 quarters = 440`.
- Record empty responses instead of aborting.
- Resume must skip completed raw partitions.
- PIT readiness must pass after the smoke.
- Duplicate financial keys must be 0 before any full-shard expansion.
- Do not pre-register profitability factors from the first10 smoke.

## Acceptance Criteria

- `shard_backfill_smoke.json` is written.
- `limited_backfill_smoke.json` is written.
- `tushare_financial_pit_readiness.json` is written.
- Processed rows are non-zero.
- `duplicate_rows == 0`.
- `missing_asset_id_rows == 0`.
- PIT readiness passes.
- Startup gate advances to a full-shard data-quality backfill only if the above gates pass.

## Non-Goals

- No profitability-factor backtest.
- No Sharpe/profit/win-rate claims.
- No GitHub push.
- No broker, account, order, or live-trading action.
