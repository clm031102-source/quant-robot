# CN Stock Tushare Financial Ingestion Smoke Round89 - 2026-06-21

## Purpose

Round89 implemented the first reusable Tushare financial indicator input path after Round88 proved that local data did not contain point-in-time profitability datasets.

This round did not mine or promote profitability factors. It built and smoke-tested the data layer needed before true profitability-quality factors can be researched.

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Dataset: `fina_indicator`
- Stage: fixture smoke and PIT-readiness validation
- Smoke output: `data/processed/tushare_fina_indicator_smoke_round89_20260621`
- Readiness output: `data/reports/tushare_financial_pit_readiness_round89_smoke_20260621`

Research only. No broker connection, no account reads, no order placement, and no live-trading action.

## What Was Built

Reusable code:

- Tushare `fina_indicator` mapper with PIT fields:
  - `ann_date`
  - `end_date`
  - `roe`
  - `roa`
  - `grossprofit_margin`
  - `netprofit_margin`
  - `netprofit_yoy`
  - `or_yoy`
  - `ocfps`
  - `cfps`
- `TushareAdapter.fetch_fina_indicator(...)`
- `run_tushare_fina_indicator_ingest(...)`
- CLI sources:
  - `tushare-fina-indicator-fixture`
  - `tushare-fina-indicator`
- readiness audit precision fix so manifest and quality-report files are not counted as financial datasets.

Processed dataset path:

- `processed/fina_indicator_inputs/frequency=1q/market=CN/year=<ann_date year>`

Raw dataset path:

- `raw/tushare/fina_indicator/period=<report_period>`

## Fixture Smoke Command

```powershell
python scripts\ingest_data.py --source tushare-fina-indicator-fixture --market CN --output-dir data\processed\tushare_fina_indicator_smoke_round89_20260621 --start-date 2024-03-31 --end-date 2024-06-30
```

Smoke result:

| Check | Result |
|---|---:|
| Dataset | `fina_indicator` |
| Downloaded periods | `20240331`, `20240630` |
| Processed rows | 4 |
| Assets | 2 |
| Missing numeric rows | 0 |
| Duplicate rows | 0 |
| Announcement date range | 2024-04-25 to 2024-07-25 |
| Report period range | 2024-03-31 to 2024-06-30 |

## PIT Readiness Command

```powershell
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\tushare_fina_indicator_smoke_round89_20260621 --output-dir data\reports\tushare_financial_pit_readiness_round89_smoke_20260621
```

Readiness result:

| Check | Result |
|---|---:|
| Files scanned | 5 |
| Financial-like data files | 3 |
| PIT-ready data files | 3 |
| Passes readiness | true |
| Blockers | none |

The three PIT-ready files were:

- raw `period=20240331`
- raw `period=20240630`
- processed `fina_indicator_inputs` for announcement year 2024

## Decision

Round89 proves the project can now represent true profitability-quality data in the required PIT shape.

It does not yet prove that live Tushare financial data is available locally, complete, or long-history ready. It also does not justify mining or promoting profitability factors yet.

Promotion counts after Round89:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New factor candidates from Round89: 0
- New reusable process artifacts: mapper, adapter method, ingest module, CLI source, readiness audit precision fix, tests, plan, report

## Required Next Direction

Round90 should be:

`round90_tushare_financial_live_smoke_or_backfill`

Minimum scope:

- run a small real Tushare `fina_indicator` smoke only if the token is available through the approved environment-secret path;
- do not print or commit any token;
- verify the real returned schema has `ann_date`, `end_date`, and at least one profitability field;
- rerun PIT readiness against the real smoke root;
- if real smoke passes, prepare a long-history quarterly backfill plan;
- only after real long-history PIT data exists should profitability-quality factors be pre-registered and backtested.

## Repeatable Process Change

Future profitability-factor rounds must confirm:

- `fina_indicator` or equivalent PIT financial inputs exist;
- `ann_date` is used as the information-availability date;
- report-period `end_date` alone is never used as the trading date;
- daily-basic valuation proxies are not relabeled as profitability;
- long-cycle, costed, capacity-aware walk-forward validation remains mandatory before any promotion claim.
