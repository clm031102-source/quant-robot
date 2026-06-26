# CN Stock Calendar Seasonality Residual Prescreen Round164

## Executive Summary

- Source preregistration: `docs/research/cn_stock_cn_calendar_seasonality_preregistration_round163_2026-06-23.md`.
- Real data window: 2015-01-05 to 2025-12-31.
- Assets: 5,707 CN stocks.
- Bar rows: 10,785,537.
- Factor rows: 13,343,481.
- Label rows: 10,751,318.
- Candidates tested: 8 frozen Round163 calendar-seasonality candidates.
- Residual research leads: 1.
- Portfolio grid candidates: 0.
- Promotion candidates: 0.
- Next direction: `round165_cn_calendar_seasonality_cost_capacity_preflight`.

## Lead Candidate

`pre_holiday_liquidity_avoidance_5_3` is the only residual research lead.

| Metric | Value |
|---|---:|
| Raw mean Spearman IC | 0.0379 |
| Industry-neutral mean IC | 0.0547 |
| Residual mean IC | 0.0487 |
| Residual ICIR | 0.6560 |
| Residual IC positive rate | 74.29% |
| Residual yearly failure count | 0 |
| 2015 residual IC observations | 21 |
| 2015 residual mean IC | 0.0488 |
| 2015 stress failure | false |
| High reference redundancy count | 0 |
| High style exposure count | 0 |
| Calendar coverage | pass |

Interpretation: the signal is not just the generic reversal/liquidity/low-volatility reference cluster in this residual prescreen. It also does not rely on a single year, and it passes the specific 2015 stress breakout used in this gate.

## Rejected Candidates

| Factor | Residual IC | Residual ICIR | Main blockers |
|---|---:|---:|---|
| `turn_of_month_reversal_liquid_5_5` | 0.0242 | 0.320 | 2025 yearly failure; high size/liquidity/vol exposure. |
| `weekday_monday_reversal_quality_5_5` | 0.0210 | 0.252 | Yearly instability; reference redundancy; style exposure. |
| `month_start_liquidity_recovery_5_5` | 0.0154 | 0.225 | Weak industry-neutral IC; weak residual IC; yearly instability; style exposure. |
| `month_end_crowding_exhaustion_10_5` | 0.0112 | 0.145 | Weak residual IC/ICIR/positive rate; yearly instability. |
| `quarter_end_liquidity_window_reversal_20_5` | 0.0045 | 0.056 | Weak residual signal; yearly instability; style exposure. |
| `post_holiday_gap_reversal_quality_3_5` | -0.0028 | -0.031 | Weak residual signal; reference redundancy; 2015 stress failure. |
| `turn_of_month_residual_momentum_20_5` | -0.0011 | -0.014 | Weak neutral/residual signal; reference redundancy; style exposure; 2015 stress failure. |

## 2015 And Redundancy Read

The 2015 audit did what it was supposed to do: it separated real cross-period survival from full-sample averaging.

- The lead `pre_holiday_liquidity_avoidance_5_3` had 21 residual IC observations in 2015 and mean IC 0.0488, so it did not pass by avoiding 2015.
- `post_holiday_gap_reversal_quality_3_5` and `turn_of_month_residual_momentum_20_5` failed the 2015 stress gate, which means their full-sample averages are not enough evidence.
- `turn_of_month_reversal_liquid_5_5` looked superficially usable, but failed 2025 and had high style exposure; it should not be converted directly into a portfolio.

## Decision

Do not promote anything. Do not broaden the calendar family or tune holiday windows yet.

Only `pre_holiday_liquidity_avoidance_5_3` earns a Round165 cost/capacity preflight. Round165 must test whether this residual IC translates into tradable portfolio behavior after turnover, holiday liquidity thinning, slippage, capacity, drawdown, and no-trade window checks.
