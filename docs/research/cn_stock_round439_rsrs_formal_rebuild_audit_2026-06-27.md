# CN Stock Round439 RSRS Formal Rebuild Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round438 showed a promising projection for `rsrs_zscore_18_60` top10 with 1.50x tilt on the delayed-exit lane. Round439 tests whether that uplift survives a formal cohort-entry rebuild.

The control is strict: keep the current delayed-exit construction unchanged and only replace the public factor tilt from the current Alpha101 open-close bottom10 layer to RSRS z top10.

## Formal Rebuild

Command output:

- `data/reports/round439_24h_profit_sprint_delayed_exit_rsrs_z_top10_formal_rebuild_20260627`

Construction:

- trade source: `data/reports/round432_24h_profit_sprint_delayed_exit_return_repair_20260627/delayed_exit_trade_rows.csv`;
- return column: `delayed_exit_weighted_return`;
- exit date column: `delayed_exit_date`;
- Dragon-Tiger cash filter: `dragon_hot_chase_20d`;
- public factor: `rsrs_zscore_18_60`;
- side: top 10%;
- multiplier: 1.50x;
- entry-timed vol target: 8%, 84-event lookback, max exposure 1.00;
- entry-timed self-risk: prior 21 closed events below 0 gets 0.80x exposure.

Factor coverage:

- candidate-universe trades: 26,090;
- matched trades: 25,784;
- missing share: 1.17%;
- public tilted trades: 2,916.

## Result

The formal rebuild failed to reproduce the Round438 projection uplift.

| Candidate | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Leave-One-Year Min Ann. | Best 3M Log Share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base` | 6.663% | 218.46% | 0.968 | 0.496 | -26.21% | 41.33% | 5.001% | 45.72% |
| `formal_rsrs_z_top10` | 6.337% | 201.42% | 0.927 | 0.477 | -27.11% | 41.10% | 4.770% | 48.60% |

## OOS And Beta

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Strict OOS Pass | Worst OOS DD | Beta-Hedged Ann. | Beta-Hedged Overlap | Beta-Hedged DD | Alpha t-stat |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base` | 10.043% | 0.831 | 90.00% | -19.30% | 7.502% | 0.797 | -12.67% | 4.40 |
| `formal_rsrs_z_top10` | 9.752% | 0.826 | 76.67% | -19.77% | 7.095% | 0.756 | -13.59% | 4.19 |

The RSRS formal rebuild is worse on every promotion-relevant comparison:

- lower full-sample annualized and total return;
- lower Sharpe and overlap Sharpe;
- deeper full-sample drawdown;
- weaker leave-one-year robustness;
- lower OOS pass rate;
- weaker beta-hedged return and overlap;
- lower alpha t-stat.

## Decision

Reject `round439_delayed_exit_rsrs_z_top10_m150` as a replacement or paper-simulation candidate.

Round438's RSRS projection is now classified as a projection false positive. It remains useful as a process lesson: public-indicator overlays must pass formal cohort-entry rebuild before they can enter the simulation shortlist.

Next direction:

- formally rebuild `cash_public_anti_supertrend_top10` using the same cohort-entry path with public-factor multiplier set to 0.0;
- if anti-supertrend fails, rotate away from public technical overlays and test a different factor family with entry-known data.
