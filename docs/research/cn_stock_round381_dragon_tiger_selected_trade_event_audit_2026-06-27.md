# CN Stock Round381 - Dragon-Tiger Selected-Trade Event Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock event-factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Test whether Dragon-Tiger attention events identify bad trades inside the current primary low-turnover replacement basket.

This is a microstructure/event-risk audit, not a standalone Dragon-Tiger TopN strategy.

## Output

`data/reports/round381_24h_profit_sprint_dragon_tiger_selected_trade_event_audit_20260627`

Inputs:

- selected trades: `round338` `replace_drop_turnover_f_low10_trades_with_tradeability.parquet`;
- Dragon-Tiger stock-day cache: `data/processed/round232_dragon_tiger_attention_reversal_20260624`.

## Coverage

- selected trade rows: 26,450;
- Dragon-Tiger rows: 159,675;
- Dragon-Tiger assets: 6,391.

Recent selected-trade flags:

- any Dragon-Tiger event 20d: 797 trades;
- net buy 20d: 450 trades;
- institution net buy 20d: 455 trades;
- hot chase 20d: 359 trades;
- hot sell 60d: 1,120 trades.

## Best Risk Tags

Trade-level entry-cash contribution sums:

| Flag | Trades | Contribution | Cashing Delta |
|---|---:|---:|---:|
| `dragon_hot_chase_20d` | 359 | -0.0310 | +0.0310 |
| `dragon_net_buy_20d` | 450 | -0.0272 | +0.0272 |
| `dragon_inst_net_buy_20d` | 455 | -0.0264 | +0.0264 |
| `dragon_hot_sell_60d` | 1,120 | -0.0224 | +0.0224 |
| `dragon_any_20d` | 797 | -0.0116 | +0.0116 |

Interpretation: recent hot Dragon-Tiger attention, especially hot-chase/net-buy attention, behaves like a short-term crowding/attention risk label inside the low-turnover replacement basket.

## Decision

Promote `dragon_hot_chase_20d` and `dragon_net_buy_20d` to a research quickcheck.

Do not promote to simulation. It still needs event-calendar-safe portfolio reconstruction, OOS split, block audit, cost stress, and parity gating.
