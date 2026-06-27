# CN Stock Round386 - Market Temperature Overlay

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round386 tested whether broad China market temperature states can improve the current shortlist event-return lanes.

This is a portfolio exposure overlay, not a new stock-selection factor. The tested overlays use point-in-time market state features available before the event decision date:

- hot turnover;
- high cross-sectional dispersion;
- hot turnover or high dispersion;
- hot turnover and high dispersion;
- cold liquidity.

The overlay linearly scales already validated event returns. It does not regenerate raw events and does not change selected stocks.

## Outputs

- Projection: `data/reports/round386_24h_profit_sprint_market_temperature_overlay_projection_20260627`
- OOS split: `data/reports/round386_24h_profit_sprint_market_temperature_overlay_oos_20260627`

## Best Full-Sample Rows

| Candidate | Ann. | Overlap | Max DD | Risk State Share |
|---|---:|---:|---:|---:|
| `dragon_hot_100` | 6.45% | 0.532 | -28.57% | 0.00% |
| `primary_100` | 6.35% | 0.517 | -28.88% | 0.00% |
| `dragon_hot_100_temp_high_dispersion_mult_0.75` | 6.30% | 0.535 | -27.77% | 2.64% |
| `dragon_hot_100_temp_high_dispersion_mult_0.50` | 6.16% | 0.538 | -26.96% | 2.64% |
| `primary_075` | 5.99% | 0.530 | -24.74% | 0.00% |
| `dragon_hot_100_temp_high_dispersion_mult_0.00` | 5.86% | 0.540 | -25.33% | 2.64% |

## OOS Split

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `dragon_hot_100` | 8.02% | 0.869 | -23.68% | 90.00% |
| `primary_100` | 7.86% | 0.845 | -24.00% | 90.00% |
| `dragon_hot_100_temp_high_disp_050` | 7.74% | 0.831 | -21.68% | 90.00% |
| `primary_100_temp_high_disp_050` | 7.58% | 0.807 | -21.97% | 90.00% |
| `dragon_hot_100_temp_high_disp_000` | 7.46% | 0.791 | -19.64% | 90.00% |
| `primary_075` | 6.95% | 0.828 | -19.55% | 90.00% |

## Decision

Do not add a market-temperature overlay to the simulation shortlist.

High-dispersion scaling improves drawdown and sometimes overlap Sharpe, but it gives up return and does not beat the existing `dragon_hot_100` or `primary_100` lanes on the return objective.

Keep it as a defensive reference only:

`dragon_hot_100_temp_high_dispersion_mult_0.50`

This can be useful if the next phase explicitly prioritizes drawdown below roughly 22%, but it is not the best 24h profit-sprint candidate.

## Process Lesson

Broad market states should be treated as risk-budget overlays unless they improve both full-sample and OOS return. In this sprint, market temperature helps risk optics but does not create alpha.
