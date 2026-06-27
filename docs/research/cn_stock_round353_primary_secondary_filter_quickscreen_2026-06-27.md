# CN Stock Round353 - Primary Secondary Filter Quickscreen

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round352 showed that direct daily-basic value/yield/public-anomaly TopN portfolios are not competitive. Round353 therefore changed the use of daily-basic information:

- do not use value/yield/liquidity as standalone ranking factors;
- use them only as secondary filters on the already-useful `primary_low10_vol6` selected basket;
- cash filtered entries instead of replacing them, so this is a defensive overlay, not a new alpha family.

Output:

`data/reports/round353_24h_profit_sprint_primary_secondary_filter_quickscreen_20260627`

2026 final holdout remains unused.

## Method

Source event/trade surface:

- official Round339 `replace_drop_turnover_f_low10_vol_target_6_lb84` event exposure;
- Round341 selected-trade parquet;
- current cost rate 10 bps;
- CSI500 risk-off multipliers: 100%, 75%, 50%.

Validation:

| Check | Max Abs Diff |
|---|---:|
| Base selected basket reproduces official 10 bps event stream | 1.84e-16 |

Tested selected-basket filters:

- cash selected entries with top 20% PB;
- cash selected entries with top 20% PE;
- cash selected entries with top 20% PS;
- cash selected entries with top 20% volume ratio;
- cash selected entries with bottom 20% market cap;
- cash selected entries with bottom 20% dividend yield;
- selected combinations of the above.

Ranks are computed within the selected basket on each signal date, not on the full universe.

## Best Full-Sample Rows

| Filter | Risk-Off Mult. | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| `cash_ps_high20_selected` | 50% | +119.29% | +4.86% | 1.076 | 0.573 | -15.90% |
| `cash_ps_high20_selected` | 75% | +129.42% | +5.15% | 1.059 | 0.568 | -19.46% |
| `cash_ps_high20_selected` | 100% | +139.76% | +5.43% | 1.025 | 0.554 | -22.87% |
| `cash_pe_high20_selected` | 50% | +111.82% | +4.64% | 1.017 | 0.540 | -15.96% |
| `base_all_selected` | 50% | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% |
| `base_all_selected` | 75% | +161.99% | +5.99% | 0.989 | 0.530 | -24.74% |

## Cross-Split Rows

| Filter | Risk-Off Mult. | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|
| `cash_ps_high20_selected` | 50% | +5.01% | 0.862 | -12.02% | 90.00% |
| `base_all_selected` | 100% | +7.86% | 0.845 | -24.00% | 90.00% |
| `base_all_selected` | 75% | +6.95% | 0.828 | -19.55% | 90.00% |
| `cash_pe_high20_selected` | 100% | +6.31% | 0.826 | -19.26% | 90.00% |
| `base_all_selected` | 50% | +6.05% | 0.824 | -14.87% | 90.00% |
| `cash_volume_ratio_high20_selected` | 75% | +5.35% | 0.814 | -15.84% | 90.00% |

## Interpretation

The useful result is the PS filter:

`cash_ps_high20_selected + zz500_mom120_neg_mult_0.50`

It does not beat the current high-return or balanced candidates on return, but it improves defensive quality:

- higher full-sample overlap Sharpe than the existing 50% defensive baseline;
- max drawdown around -16%;
- 90% cross-split strict pass at current cost;
- still uses the proven primary selection surface.

## Decision

Promote the PS filter to Round354 cost/beta quickcheck.

Do not promote PB, PE, dividend, size, or volume-ratio filters yet. They may remain comparison rows, but the PS filter is the only one with a clear low-drawdown/overlap improvement profile in this quickscreen.
