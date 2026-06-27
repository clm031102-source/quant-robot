# CN Stock Round438 Public Indicator Delayed-Exit Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round438 rotates away from the ZZ500-regime and quarter-end tuning lanes and checks entry-known public technical indicators on the current delayed-exit simulation lane.

Indicator families checked:

- RSRS z-score and skew;
- SuperTrend, Smart Money, and OBV;
- RSI, Bollinger, Donchian, and MACD;
- ADX, KAMA, Aroon, and Williams trend-state style filters.

This round asks whether any public indicator adds useful return, risk control, or robustness on top of the current delayed-exit candidate without using realized future return as an entry filter.

## Execution Note

A first attempt to recompute the full public-factor source for 19 factors over the long sample timed out after about five minutes. The process was stopped and not reused.

Root cause: full source rematerialization is too slow for the 24h sprint loop and duplicates already materialized Round404 data.

Process fix:

- reuse `data/reports/round404_24h_profit_sprint_all_public_factor_source_for_dragon_hot_20260627/public_factor_values_for_shortlist.parquet`;
- only run small pre-registered cash-filter and tilt screens;
- treat sparse public factors as diagnostic overlays unless a later formal rebuild proves the effect.

## Inputs And Outputs

Core delayed-exit template:

- `data/reports/round432_24h_profit_sprint_delayed_exit_m150_20260627/simulation_shortlist_entry_timed_events.csv`
- `data/reports/round432_24h_profit_sprint_delayed_exit_return_repair_20260627/delayed_exit_trade_rows.csv`

Public factor source:

- `data/reports/round404_24h_profit_sprint_all_public_factor_source_for_dragon_hot_20260627/public_factor_values_for_shortlist.parquet`

Round438 outputs:

- cash-filter screen: `data/reports/round438_24h_profit_sprint_public_indicator_delayed_exit_cash_filter_20260627`
- tilt screen: `data/reports/round438_24h_profit_sprint_public_indicator_delayed_exit_tilt_20260627`
- OOS audit: `data/reports/round438_24h_profit_sprint_public_indicator_delayed_exit_oos_20260627`
- block audit: `data/reports/round438_24h_profit_sprint_public_indicator_delayed_exit_block_audit_20260627`
- beta audit: `data/reports/round438_24h_profit_sprint_public_indicator_delayed_exit_beta_20260627`
- shortlist-level statistical check: `data/reports/round438_24h_profit_sprint_public_indicator_delayed_exit_stat_reality_check_20260627`

## Quick Screen Results

The cash-filter screen tested 26 candidate masks. Only one passed the quick improvement gate:

- `cash_public_anti_supertrend_top10`
- factor: `supertrend_volume_confirmed_10_3_20`
- side: top 10%;
- action: cash flagged trades;
- role: defensive overlay candidate.

The tilt screen tested the same 26 public-indicator candidates. The strongest return-enhancement lead was:

- `tilt_public_rsrs_z_top10`
- factor: `rsrs_zscore_18_60`
- side: top 10%;
- multiplier: 1.50x;
- role: return-enhancement candidate for formal rebuild.

Close runner-up:

- `tilt_public_rsrs_skew_top10`
- factor: `rsrs_skew_18_60`
- side: top 10%;
- multiplier: 1.50x.

## Long-Sample Metrics

Block-audit metrics use the repaired delayed-exit return streams, not the quick-screen headline alone.

| Candidate | Role | Annualized | Total Return | Overlap Sharpe | Max DD | Win Rate | Leave-One-Year Min Ann. | Best 3M Log Share |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `base` | current default | 6.663% | 218.46% | 0.496 | -26.21% | 41.33% | 5.001% | 45.72% |
| `tilt_rsrs_z_top10` | return enhancement | 7.373% | 258.74% | 0.506 | -26.75% | 41.22% | 5.434% | 45.18% |
| `tilt_rsrs_skew_top10` | return enhancement runner-up | 7.356% | 257.70% | 0.505 | -26.80% | 41.10% | 5.414% | 45.16% |
| `cash_anti_supertrend_top10` | defensive overlay | 6.723% | 221.68% | 0.526 | -23.98% | 41.99% | 5.203% | 42.23% |

Interpretation:

- RSRS z/skew top10 improves annualized return, total return, overlap Sharpe, and leave-one-year minimum annualized return versus base, but slightly worsens full-sample drawdown.
- Anti-supertrend cashing improves overlap Sharpe, max drawdown, win rate, and best-month concentration, but does not create the highest-return lane.

## OOS And Beta Checks

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Strict OOS Pass | Worst OOS DD | Beta-Hedged Ann. | Beta-Hedged Overlap | Beta-Hedged DD | Alpha t-stat |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base` | 10.043% | 0.831 | 90.00% | -19.30% | 7.502% | 0.797 | -12.67% | 4.40 |
| `tilt_rsrs_z_top10` | 10.832% | 0.854 | 90.00% | -21.15% | 8.235% | 0.817 | -13.61% | 4.41 |
| `tilt_rsrs_skew_top10` | 10.791% | 0.854 | 90.00% | -21.30% | 8.217% | 0.816 | -13.43% | 4.41 |
| `cash_anti_supertrend_top10` | 10.108% | 0.858 | 90.00% | -18.29% | 7.589% | 0.824 | -11.60% | 4.62 |

Interpretation:

- RSRS z top10 has the best return uplift and keeps the OOS pass rate at 90%, but it accepts roughly 1.9 percentage points worse worst-OOS drawdown than base.
- Anti-supertrend has the cleanest risk profile and best beta-hedged overlap/drawdown, but the return uplift is modest.

## Statistical Reality Check

Round438 ran a shortlist-level statistical reality check across four rows: base, RSRS z tilt, RSRS skew tilt, and anti-supertrend cash filter.

Result:

- hypothesis count: 4;
- deflated-Sharpe pass count: 4;
- FDR significant count: 4;
- statistical candidate count: 4;
- common FDR q-value around 0.03553.

Important caveat: this is a shortlist-level check after earlier screening, not a complete multiple-testing accounting for every public-indicator idea tried today. It supports continued simulation-observation work; it does not prove that RSRS or anti-supertrend is an independent final alpha.

## Decision

Round438 adds two useful leads, but neither is paper-ready yet:

1. Promote `tilt_public_rsrs_z_top10` to the next formal rebuild/audit round as the return-enhancement candidate.
2. Carry `cash_public_anti_supertrend_top10` as a defensive overlay watchlist candidate.
3. Keep `tilt_public_rsrs_skew_top10` as a runner-up only, because it is very close to RSRS z and likely redundant.
4. Stop broad public-indicator blind screening unless the source is already cached and the hypothesis count is pre-registered.

The most useful next step is a formal Round439 rebuild for RSRS z top10 at cohort-entry granularity, followed by cost, OOS, block-dependence, beta, and statistical checks using the same gates as the current delayed-exit pack.
