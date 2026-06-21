# CN Stock Tushare Financial Profitability PIT Readiness Round88 - 2026-06-21

## Purpose

Round88 rotated away from public QVM after Round87 had 0 accepted walk-forward folds. The goal was to answer one narrow question before mining true profitability and quality factors:

Can the current local Tushare data support point-in-time financial statement factors such as ROE, ROA, margins, profit growth, cash-flow quality, accruals, and earnings-quality signals?

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Stage: financial input readiness, not factor promotion
- Output: `data/reports/tushare_financial_pit_readiness_round88_20260621`

Research only. No broker connection, no account reads, no order placement, and no live-trading action.

## Command

```powershell
python scripts\run_tushare_financial_pit_readiness.py --root data\processed\cn_stock_long_history_2015_202306 --root data\processed\office_desktop_20260617_daily_basic_factor_inputs --output-dir data\reports\tushare_financial_pit_readiness_round88_20260621 --allow-not-ready
```

## Readiness Result

| Check | Result |
|---|---:|
| Files scanned | 6,939 |
| Financial-like datasets found | 0 |
| PIT-ready datasets found | 0 |
| Passes readiness | false |
| Blocker | `missing_financial_statement_or_indicator_dataset` |

Inspected roots:

- `data\processed\cn_stock_long_history_2015_202306`
- `data\processed\office_desktop_20260617_daily_basic_factor_inputs`

The first root currently has only:

- `bars`
- `factor_inputs`
- `moneyflow_inputs`

The daily-basic authority config currently points to those two daily-basic roots only:

- `data/processed/cn_stock_long_history_2015_202306`
- `data/processed/office_desktop_20260617_daily_basic_factor_inputs`

## Code-Level Evidence

The current Tushare adapter supports:

- daily OHLCV
- ETF daily OHLCV
- daily basic
- moneyflow
- adjustment factor
- trade calendar
- stock basic
- fund basic

It does not yet expose financial statement or indicator endpoints such as:

- `fina_indicator`
- `income`
- `balancesheet`
- `cashflow`

The current Tushare mapping layer has `DAILY_BASIC_COLUMNS` for valuation, turnover, size, and dividend fields:

- `pe`, `pe_ttm`, `pb`, `ps`, `ps_ttm`
- `dv_ratio`, `dv_ttm`
- `turnover_rate`, `turnover_rate_f`, `volume_ratio`
- `total_share`, `float_share`, `free_share`, `total_mv`, `circ_mv`

It does not currently map profitability statement columns such as:

- `roe`
- `roa`
- `grossprofit_margin`
- `netprofit_margin`
- `netprofit_yoy`
- `or_yoy`
- `ocfps`
- `cfps`

## Decision

Round88 did not pre-register profitability factors.

Reason: doing so with the current data would either:

1. reuse valuation and liquidity proxies and incorrectly label them as profitability factors; or
2. risk look-ahead bias if financial report announcement dates are not modeled correctly.

Therefore the correct decision is to block profitability-quality factor mining until a point-in-time financial input dataset exists locally and passes readiness.

Promotion counts after Round88:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New factor candidates from Round88: 0
- New reusable process artifacts: 1 readiness audit module, 1 CLI, 2 unit test files, 1 research report

## Required Next Direction

Round89 should be:

`round89_tushare_financial_ingestion_design_and_smoke`

Minimum scope:

- add adapter support for `fina_indicator` first;
- design optional mappings for `income`, `balancesheet`, and `cashflow`;
- require point-in-time columns such as `ann_date`, `f_ann_date`, and `end_date`;
- store financial inputs under a separate ignored processed data path;
- rerun the Round88 readiness audit after a small smoke ingest;
- only pre-register profitability-quality factors if the readiness audit passes.

Minimum factor concepts to consider only after readiness passes:

- ROE / ROA quality;
- gross and net margin quality;
- operating cash-flow quality;
- profit growth and revenue growth stability;
- accruals or cash-flow-to-income quality;
- profitability improvement after publication lag.

## Repeatable Process Change

Before any future round that claims to mine profitability or quality factors, the startup gate must confirm:

- the Round88 readiness audit has been read;
- financial PIT data readiness passed;
- announcement-date or publication-date lag is enforced;
- daily-basic valuation proxies are not being substituted for true profitability;
- no financial factor backtest starts before PIT input readiness clears.
