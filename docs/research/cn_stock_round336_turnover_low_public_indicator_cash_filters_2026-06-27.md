# CN Stock Round336 - Public Indicator Cash Filters on Turnover-Low Base

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

The user raised a valid critique: factor mining should not blindly continue along only moneyflow or turnover variants. This round tested whether public technical indicators can improve the current best CN stock base:

`turnover_rate_low_top50_hold20_reb5_cost5 + entry_cash`

Instead of running public indicators as standalone TopN factors, this round used them as cash filters inside already selected low-turnover holdings.

Families tested:

- public technical: RSI, Bollinger, Donchian, MACD;
- RSRS: slope, z-score, right-skew, reversal;
- trend-volume: SuperTrend, smart-money pressure, OBV breakout and anti variants;
- trend-strength state: ADX, choppiness, KAMA efficiency, Aroon, Williams, composite.

Output:

`data/reports/round336_24h_profit_sprint_turnover_low_public_indicator_cash_filters_20260627`

2026 final holdout remains unused.

## Method

Inputs:

- 20,841 entry-allowed turnover-low trades from Round333;
- 327 unique traded assets;
- 22 public indicator factor names;
- 66 filter hypotheses: bottom20, top20, and 2017-2018 failure-worst side for each indicator.

Validation:

- full 834 exit-date calendar;
- zero-return dates preserved;
- `entry_date` decision alignment;
- cost already embedded in trade returns;
- cross-split robustness over train/test split schemes 2/1, 3/1, 4/1, and 5/1.

## Baseline

`cash_low_turnover_f_bottom20`

| Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Win Rate |
|---:|---:|---:|---:|---:|---:|
| +107.79% | +4.52% | 0.750 | 0.414 | -28.01% | 40.89% |

This is the current filter baseline from Round333.

## Best Public-Filter OOS Rows

These are the best failure-worst public indicator filters by cross-split OOS overlap.

| Filter | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `cash_public_bollinger_reversal_20_failure_worst_top20` | +5.11% | +3.25% | 0.617 | 0.293 | -15.76% | 90.18% |
| `cash_public_obv_breakout_low_tail_20_failure_worst_bottom20` | +2.01% | +1.37% | 0.580 | 0.241 | -8.21% | 77.44% |
| `cash_public_rsrs_reversal_18_60_failure_worst_bottom20` | +4.92% | +3.10% | 0.563 | 0.252 | -16.18% | 74.32% |
| `cash_public_macd_histogram_12_26_9_failure_worst_top20` | +4.73% | +3.03% | 0.560 | 0.264 | -15.63% | 74.32% |
| `cash_public_rsrs_zscore_18_60_failure_worst_top20` | +4.70% | +2.94% | 0.553 | 0.243 | -15.92% | 74.32% |

## Full-Sample Reality Check

The public filters do not beat the current turnover-low repair baseline on full sample.

The top public rows by full-sample overlap are around:

- annualized return: +3.6%;
- overlap Sharpe: about 0.35-0.36;
- max drawdown: about -28% to -30%.

That is weaker than `cash_low_turnover_f_bottom20`:

- annualized return: +4.52%;
- overlap Sharpe: 0.414;
- max drawdown: -28.01%.

## Decision

Do not promote any Round336 public indicator cash filter.

The useful lesson is negative but important:

- public technical indicators are not a clean direct improvement on the low-turnover base;
- they can act as risk labels, especially Bollinger overextension and OBV low-tail states;
- direct filtering removes too much return from the low-turnover anomaly.

## Next Direction

Keep `cash_low_turnover_f_bottom20` as the best current repair baseline.

Next, test interaction filters that are closer to the failure mechanism:

1. combine low-turnover bottom exclusion with valuation/capacity stress only when both are present;
2. test replacement instead of cashing, because public filters may remove bad names but also reduce gross exposure;
3. test industry/board neutral low-turnover selection so the base signal is less dependent on 2015-2018 structure.
