# CN Stock Round380 - Forecast/Express Selected-Trade Event Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock event-factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Test whether Tushare forecast/express events identify bad trades inside the current primary low-turnover replacement basket.

This deliberately avoids another standalone event-factor sweep. The question is narrower: can recent forecast/express events act as a defensive selected-trade filter?

## Output

`data/reports/round380_24h_profit_sprint_forecast_express_selected_trade_event_audit_20260627`

Inputs:

- selected trades: `round338` `replace_drop_turnover_f_low10_trades_with_tradeability.parquet`;
- forecast/express cache: `data/processed/round255_forecast_express_event_cache_20260625`.

## Coverage

- selected trade rows: 26,450;
- forecast rows: 78,573, assets: 5,728;
- express rows: 20,304, assets: 4,280.

Recent selected-trade flags:

- negative forecast 60d: 1,793 trades;
- negative forecast 120d: 3,080 trades;
- negative express 60d: 214 trades;
- negative express 120d: 397 trades;
- positive forecast 60d: 2,129 trades;
- positive forecast 120d: 3,815 trades.

## Result

The event flags do not isolate a bad-trade pocket.

Trade-level entry-cash contribution sums:

- negative forecast 60d: +0.0660;
- negative forecast 120d: +0.1157;
- negative express 60d: +0.0069;
- negative express 120d: +0.0210;
- positive forecast 60d: +0.1355;
- positive forecast 120d: +0.1964.

Several negative-event groups lose money in 2017-2018 or 2022, but full-cycle contribution remains positive. A blanket cash filter would lower total return.

## Decision

Reject forecast/express selected-trade cash filters for the current primary basket.

Keep the forecast/express event cache as reusable infrastructure, but do not spend more sprint time on simple recent negative/positive forecast or express event filters unless a regime-conditional design is pre-registered.
