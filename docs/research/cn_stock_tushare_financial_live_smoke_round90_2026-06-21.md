# CN Stock Tushare Financial Live Smoke Round90 - 2026-06-21

## Purpose

Round90 verified that the new `fina_indicator` ingestion path can pull a real Tushare financial indicator row without leaking secrets or using broker/live-trading boundaries.

This round did not mine or promote profitability factors. It only verified the live Tushare schema and PIT shape on a tiny sample.

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Dataset: real Tushare `fina_indicator`
- Sample: `000001.SZ`, period `20240331`
- Processed output: `data/processed/tushare_fina_indicator_live_smoke_round90_20260621_symbol`
- Readiness output: `data/reports/tushare_financial_pit_readiness_round90_live_smoke_20260621`

Research only. No broker connection, no account reads, no order placement, and no live-trading action.

## Initial Failure And Root Cause

The first live smoke tried period-only `fina_indicator` ingestion:

```powershell
python scripts\ingest_data.py --source tushare-fina-indicator --market CN --output-dir data\processed\tushare_fina_indicator_live_smoke_round90_20260621 --start-date 2024-03-31 --end-date 2024-03-31
```

It failed because the real Tushare endpoint required `ts_code` for this request path. The fix was not to broaden the request. The ingest path was extended to support an explicit symbol-scoped smoke list.

## Successful Live Smoke Command

```powershell
python scripts\ingest_data.py --source tushare-fina-indicator --market CN --output-dir data\processed\tushare_fina_indicator_live_smoke_round90_20260621_symbol --start-date 2024-03-31 --end-date 2024-03-31 --symbols 000001.SZ
```

Result:

| Check | Result |
|---|---:|
| Dataset | `fina_indicator` |
| Downloaded request | `000001.SZ:20240331` |
| Processed rows | 1 |
| Assets | 1 |
| Announcement date | 2024-04-20 |
| Report period | 2024-03-31 |
| Duplicate rows | 0 |
| Missing asset IDs | 0 |
| Missing numeric rows | 2 |
| Missing numeric columns | `grossprofit_margin`, `roa` |

The real row contained usable profitability fields including:

- `roe`
- `netprofit_margin`
- `netprofit_yoy`
- `or_yoy`
- `ocfps`
- `cfps`

## PIT Readiness Command

```powershell
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\tushare_fina_indicator_live_smoke_round90_20260621_symbol --output-dir data\reports\tushare_financial_pit_readiness_round90_live_smoke_20260621
```

Readiness result:

| Check | Result |
|---|---:|
| Files scanned | 4 |
| Financial-like data files | 2 |
| PIT-ready data files | 2 |
| Passes readiness | true |
| Blockers | none |

## Decision

Round90 proves that real Tushare `fina_indicator` data can be pulled through the new ingestion path and recognized by the PIT readiness gate.

It still does not justify mining profitability factors yet, because a one-stock, one-quarter smoke is not enough for cross-sectional factor research.

Promotion counts after Round90:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New factor candidates from Round90: 0
- New useful data capability: real symbol-scoped `fina_indicator` smoke passed PIT readiness

## Required Next Direction

Round91 should be:

`round91_tushare_fina_indicator_long_history_backfill_plan`

Minimum scope:

- define quarterly periods from 2015-03-31 through 2025-12-31;
- define a stock universe source and symbol batching policy;
- avoid token leakage and avoid committing data;
- respect API rate limits and resume semantics;
- run a limited multi-symbol, multi-quarter backfill smoke before full backfill;
- only after long-history PIT financial data exists should profitability factor candidates be pre-registered.
