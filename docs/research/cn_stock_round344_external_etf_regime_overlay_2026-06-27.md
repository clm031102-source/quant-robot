# CN Stock Round344 - External ETF Regime Overlay

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round344 tests external market-regime overlays for the current primary candidate.

Base candidate:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

External regime data:

- `CN_ETF_XSHG_510300` as broad HS300 proxy;
- `CN_ETF_XSHG_510500` as broad CSI500 proxy.

Every overlay decision uses ETF information available before each strategy `decision_date`.

Output:

`data/reports/round344_24h_profit_sprint_external_etf_regime_overlay_20260627`

2026 final holdout remains unused.

## Rules Tested

| Policy | Rule |
|---|---|
| `baseline_vol_target_6` | No extra external regime overlay |
| `hs300_mom120_neg_half` | Half exposure when 510300 120-day momentum is negative |
| `hs300_mom120_neg_cash` | Cash when 510300 120-day momentum is negative |
| `zz500_mom120_neg_half` | Half exposure when 510500 120-day momentum is negative |
| `both_mom120_neg_half` | Half exposure when both 510300 and 510500 120-day momentum are negative |
| `both_mom60_neg_half` | Half exposure when both 60-day momentum series are negative |
| `hs300_below_ma200_half` | Half exposure when 510300 is below its 200-day average |
| `hs300_dd252_m20_half` | Half exposure when 510300 is below its 252-day high by more than 20% |
| `hs300_vol20_gt35_half` | Half exposure when annualized 20-day 510300 volatility is above 35% |
| `hs300_mom120_or_dd20_half` | Half exposure when 510300 momentum is negative or 252-day drawdown is worse than -20% |
| `both_mom120_neg_cash` | Cash when both 120-day momentum series are negative |

## Full-Sample Result

| Policy | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Regime Exposure |
|---|---:|---:|---:|---:|---:|---:|
| `baseline_vol_target_6` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% | 100.00% |
| `zz500_mom120_neg_half` | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% | 78.66% |
| `both_mom120_neg_half` | +149.68% | +5.69% | 0.987 | 0.528 | -21.62% | 84.35% |
| `hs300_vol20_gt35_half` | +171.38% | +6.22% | 0.966 | 0.522 | -28.88% | 93.65% |
| `hs300_dd252_m20_half` | +156.64% | +5.86% | 0.975 | 0.516 | -26.55% | 87.59% |
| `both_mom120_neg_cash` | +123.63% | +4.98% | 0.918 | 0.497 | -14.48% | 68.71% |

## 2017-2018 Stress Period

| Policy | 2017-2018 Total | 2017-2018 Ann. | 2017-2018 Overlap | 2017-2018 DD |
|---|---:|---:|---:|---:|
| `baseline_vol_target_6` | -24.36% | -6.86% | -1.014 | -28.88% |
| `zz500_mom120_neg_half` | -17.66% | -4.83% | -1.063 | -20.38% |
| `both_mom120_neg_half` | -18.07% | -4.95% | -0.954 | -21.62% |
| `hs300_mom120_neg_cash` | -11.35% | -3.02% | -0.621 | -14.48% |
| `both_mom120_neg_cash` | -11.35% | -3.02% | -0.621 | -14.48% |

## Cross-Split Robustness

Aggregated across 30 one-year test folds from train/test schemes 2/1, 3/1, 4/1, and 5/1.

| Policy | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|
| `baseline_vol_target_6` | +7.86% | -10.66% | 0.845 | -24.00% | 90.00% |
| `zz500_mom120_neg_half` | +6.05% | -6.22% | 0.824 | -14.87% | 90.00% |
| `both_mom120_neg_half` | +6.12% | -6.46% | 0.815 | -15.44% | 90.00% |
| `hs300_dd252_m20_half` | +6.74% | -9.52% | 0.808 | -20.75% | 76.67% |
| `both_mom120_neg_cash` | +4.46% | -3.91% | 0.901 | -10.04% | 76.67% |

## Interpretation

External ETF regime overlays produce a better defensive candidate than the self-equity overlays from Round343.

Best balanced external defensive overlay:

`zz500_mom120_neg_half`

Why it matters:

- full-sample Sharpe improves from 0.960 to 1.001;
- overlap Sharpe improves from 0.517 to 0.536;
- max drawdown improves from -28.88% to -20.38%;
- 2017-2018 total loss improves from -24.36% to -17.66%;
- OOS strict pass remains 90.00%.

Cost:

- total return drops from +177.08% to +147.29%;
- annualized return drops from +6.35% to +5.62%.

Best crash-control external overlay:

`both_mom120_neg_cash`

Why it is not the default:

- drawdown improves to -14.48%;
- mean OOS overlap improves;
- but full-sample total return falls to +123.63%, and strict pass drops to 76.67%.

## Decision

Keep the primary high-return candidate:

`replace_drop_turnover_f_low10 + vol_target_6_lb84`

Add preferred defensive simulation variant:

`replace_drop_turnover_f_low10 + vol_target_6_lb84 + zz500_mom120_neg_half`

This is the best current risk-adjusted variant if the simulation stage wants a lower drawdown profile without collapsing OOS pass rate.

Do not use hard cash regime as default unless the paper/simulation objective explicitly prioritizes drawdown over total return.
