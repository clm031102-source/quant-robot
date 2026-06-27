# CN Stock Round427 Public Technical Cohort Screen

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round427 rotates away from Alpha101/Qlib micro-variants and tests independent public technical indicators on the same cohort-entry-timed paper-simulation harness.

The test intentionally excludes Alpha101 and Qlib names. It focuses on RSRS, Bollinger, RSI, Donchian, and MACD candidates that had adequate coverage in the Round405 public-factor source. SuperTrend, smart-money, OBV, ADX, Aroon, Williams, and KAMA variants remain diagnostics because their selected-trade missing-factor share was too high in the current source table.

## Inputs

- Trades: `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`
- Dragon-Tiger source: `data/processed/round232_dragon_tiger_attention_reversal_20260624`
- Public factor source: `data/reports/round404_24h_profit_sprint_all_public_factor_source_for_dragon_hot_20260627/public_factor_values_for_shortlist.parquet`
- Baseline: `paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08`

All tested candidates use the same cohort harness:

- Dragon-Hot cash filter;
- public technical entry tilt on selected trades;
- 10% selected-trade quantile;
- exposure multiplier 1.50x;
- entry-timed vol target 8%, lookback 84, max exposure 1.00;
- entry-timed self-risk: prior 21 closed cohort returns, 0.80x when negative.

## Full-Sample Result

| Candidate | Factor | Side | Total Return | Annualized | Sharpe | Overlap Sharpe | Max DD | Win Rate | Missing Share |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `default` | Alpha101 open-close baseline | bottom | +163.48% | 5.76% | 0.863 | 0.466 | -29.18% | 40.71% | 0.00% |
| `rsrs_zscore` | `rsrs_zscore_18_60` | top | +148.31% | 5.40% | 0.813 | 0.441 | -30.61% | 40.60% | 1.17% |
| `rsrs_right_skew` | `rsrs_right_skew_18_60` | top | +146.74% | 5.36% | 0.808 | 0.439 | -30.61% | 40.60% | 1.17% |
| `bollinger` | `bollinger_reversal_20` | top | +144.97% | 5.31% | 0.801 | 0.432 | -32.02% | 40.83% | 0.57% |
| `donchian` | `donchian_position_20` | bottom | +144.53% | 5.30% | 0.804 | 0.433 | -31.40% | 40.71% | 0.57% |
| `rsi` | `rsi_reversal_14` | top | +143.26% | 5.27% | 0.797 | 0.431 | -31.75% | 41.17% | 0.38% |
| `macd` | `macd_histogram_12_26_9` | bottom | +137.87% | 5.14% | 0.790 | 0.428 | -31.25% | 41.28% | 1.16% |

None of the public technical cohort candidates beats the default candidate. The nearest candidate, `rsrs_zscore`, has lower return, lower overlap Sharpe, lower leave-one-year floor, higher best-month concentration, and a max drawdown slightly beyond the user's -30% tolerance.

## OOS Split Result

Output:

`data/reports/round427_24h_profit_sprint_public_technical_cohort_oos_20260627`

| Candidate | Mean OOS Annualized | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `default` | 8.53% | 0.881 | -20.94% | 90.00% |
| `rsrs_zscore` | 8.24% | 0.868 | -21.43% | 90.00% |
| `rsrs_right_skew` | 8.17% | 0.862 | -21.48% | 90.00% |
| `bollinger` | 8.18% | 0.853 | -21.56% | 90.00% |
| `donchian` | 8.10% | 0.840 | -21.13% | 90.00% |
| `rsi` | 8.08% | 0.834 | -21.19% | 90.00% |
| `macd` | 7.84% | 0.824 | -20.56% | 90.00% |

OOS does not rescue the family. Every tested public technical candidate trails the default on mean OOS return and mean OOS overlap Sharpe.

## Beta Check

Output:

`data/reports/round427_24h_profit_sprint_public_technical_cohort_beta_20260627`

| Candidate | ZZ500 Beta | R2 | Hedged Annualized | Hedged Overlap | Hedged Max DD | Alpha t |
|---|---:|---:|---:|---:|---:|---:|
| `default` | 0.0474 | 0.285 | 6.23% | 0.752 | -15.10% | 3.87 |
| `rsrs_zscore` | 0.0473 | 0.284 | 5.80% | 0.701 | -16.07% | 3.62 |
| `rsrs_right_skew` | 0.0473 | 0.284 | 5.75% | 0.697 | -16.09% | 3.59 |
| `bollinger` | 0.0476 | 0.287 | 5.70% | 0.692 | -15.58% | 3.56 |

The public technical candidates have nearly the same ZZ500 exposure as the default, but weaker beta-hedged returns. This is not hidden market beta improvement.

## Decision

Do not upgrade any Round427 public technical candidate into the paper-simulation handoff pack.

The public-technical family was not useless: it answered an important user concern directly. Public indicators such as RSRS, Bollinger, RSI, Donchian, MACD, SuperTrend, and smart-money concepts were considered. In this specific event/cohort harness, the coverage-clean public technical candidates did not improve the current handoff, and the named SuperTrend/smart-money/OBV style candidates were coverage-blocked in the current source.

## Next Direction

Round428 should not keep mutating this public technical cohort line. The next highest-value search is a more independent source:

1. event-context underreaction with point-in-time availability;
2. tradeability/liquidity microstructure quality with capacity from the first screen;
3. accounting-quality or reporting-timeliness only after the source-coverage gate is broad enough;
4. or a direct paper-simulation adapter around the Round425 handoff if the 24h deadline takes priority over new discovery.
