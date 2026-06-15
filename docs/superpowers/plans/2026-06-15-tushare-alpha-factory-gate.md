# Tushare Alpha Factory Gate Plan

## Goal

Add a local-only gate that orchestrates Tushare OHLCV ingest, Tushare `daily_basic` factor-input ingest, and the Tushare daily-basic Alpha Factory. The gate must block before external calls when readiness is missing, and must never enable live trading.

## Scope

- Add an ops pack builder for the alpha-factory gate.
- Add a CLI that supports dry-run and execute modes.
- Reuse existing ingest and alpha-factory runners.
- Keep token handling in environment or ignored `.env` only.
- Write JSON, Markdown, and next-action artifacts.

## Tests

- Missing real Tushare readiness blocks before runner calls.
- Fixture execute mode runs OHLCV ingest, factor-input ingest, and alpha factory in order.
- CLI without token writes a blocked pack without exposing secrets.

## Acceptance

- Targeted tests pass.
- Full unit/integration suite passes with `PYTHONPATH=src`.
- `compileall`, project audit, and readiness checks run after implementation.
