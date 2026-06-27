# CN Stock Round419 - Entry-Timed Risk Budget Sensitivity

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round419 tuned the paper-ready Alpha101 open-close entry-timed candidate toward the user's stated tolerance for larger drawdowns, capped at roughly -30%.

This was not a new factor-family discovery. It was a risk-budget search on the currently cleanest paper-simulation lane.

## Search Space

Source:

`tilt_public_alpha101_open_close_pressure_fade_10_bottom10_m150_official_template_period_returns.csv`

Grid:

- target annual vol: 6%, 7%, 8%, 9%, 10%
- max exposure: 1.00, 1.15, 1.25
- self-risk window: 21, 42 closed events
- self-risk exposure under guard: 0.50, 0.65, 0.80
- user drawdown blocker: max drawdown below -30%

The first wider grid attempt was stopped because it was too broad for this sprint budget. The final bounded grid tested 90 combinations.

## Best Candidate

`openclose_vt10_max1p15_sr42_x0p8`

Formula:

Dragon-Hot selected entry basket plus 1.50x bottom-decile `alpha101_open_close_pressure_fade_10` tilt, entry-timed 10% volatility target, 84-event lookback, max exposure 1.15, and entry-timed self-risk exposure of 0.80 when the prior 42 closed source-event returns sum is negative.

## Full-Sample Result

| Metric | Value |
|---|---:|
| total return | +206.28% |
| annualized return | 7.00% |
| Sharpe | 0.929 |
| overlap Sharpe | 0.512 |
| max drawdown | -29.19% |
| win rate | 40.65% |
| leave-one-year min annualized return | 4.83% |
| leave-one-year min overlap Sharpe | 0.428 |
| best-month log share of total | 42.80% |
| average final exposure | 1.011 |
| self-risk guard event share | 31.77% |

## OOS Split

30 rolling splits:

| Metric | Value |
|---|---:|
| mean OOS annualized return | 9.61% |
| mean OOS overlap Sharpe | 0.874 |
| positive OOS rate | 90.00% |
| strict pass rate | 90.00% |
| worst OOS drawdown | -22.85% |
| min OOS annualized return | -9.90% |
| min OOS overlap Sharpe | -1.791 |

## Beta Audit

Benchmark: `zz500`

| Metric | Value |
|---|---:|
| beta | 0.0458 |
| R2 | 0.2485 |
| alpha annualized | 6.96% |
| alpha t-stat | 4.30 |
| beta-hedged annualized return | 6.97% |
| beta-hedged overlap Sharpe | 0.803 |
| beta-hedged max drawdown | -14.08% |

## Decision

Add this as an aggressive paper-ready candidate, separate from the more conservative Round416 entry-timed candidate.

It is closer to the user's return preference and remains inside the -30% drawdown tolerance, but the margin is narrow. It needs paper-simulation cost/accounting replay before any promotion beyond observation status.
