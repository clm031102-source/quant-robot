# CN Stock Round332 Strict Market-Stress Cap

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock low-turnover research lead.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Objective

Round331 showed that the first market-state cap was too broad because `momentum <= 0 OR drawdown <= -10%` capped more than 90% of decision dates. Round332 tests stricter ex-ante market stress definitions:

- drawdown-only cap;
- momentum-and-drawdown cap;
- lookbacks 60 and 120;
- caps 50% and 25%.

The 2026 window is intentionally not used.

## Full-Sample Diagnostics

Full-sample diagnostics look strong for 60-day stress caps:

| Policy | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Avg Exposure | Capped Decisions |
|---|---:|---:|---:|---:|---:|---:|---:|
| `market_mom_and_dd_lb60_dd10_cap25` | +258.67% | +8.02% | 1.588 | 0.774 | -7.93% | 50.35% | 70.38% |
| `market_dd_only_lb60_dd10_cap25` | +236.40% | +7.61% | 1.526 | 0.758 | -7.93% | 48.47% | 72.56% |
| `market_mom_and_dd_lb60_dd10_cap50` | +199.86% | +6.86% | 1.234 | 0.625 | -14.63% | 66.90% | 70.38% |
| `market_dd_only_lb60_dd10_cap50` | +187.34% | +6.59% | 1.196 | 0.612 | -14.76% | 65.65% | 72.56% |
| `entry_cash_no_overlay` | +107.64% | +4.51% | 0.644 | 0.355 | -35.63% | 100.00% | 0.00% |

## Walk-Forward Reality Check

Cross-split walk-forward does not confirm the full-sample winner:

| Policy | Mean OOS Ann | Min OOS Ann | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Mean Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `entry_cash_no_overlay` | +5.94% | +3.69% | 0.562 | 0.245 | -19.97% | 90.18% |
| `market_dd_only_lb120_dd10_cap50` | +2.71% | +1.58% | 0.517 | 0.202 | -10.50% | 90.18% |
| `market_mom_and_dd_lb120_dd10_cap50` | +2.71% | +1.58% | 0.517 | 0.202 | -10.50% | 90.18% |
| `market_mom_and_dd_lb120_dd10_cap25` | +1.13% | +0.56% | 0.443 | 0.134 | -8.23% | 79.32% |
| `market_dd_only_lb120_dd10_cap25` | +1.13% | +0.56% | 0.443 | 0.134 | -8.23% | 79.32% |

For each tested train-window split, the best OOS overlap-adjusted policy remained `entry_cash_no_overlay`.

## Interpretation

Positive:

- Market stress caps materially reduce 2017-2018 losses.
- 2018 annualized loss improves from about -10.86% to -5.55% at cap50 and -2.81% at cap25.
- 2017-2018 drawdown improves from about -26.8% to about -14.4% at cap50 and -7.5% to -7.9% at cap25.

Negative:

- The full-sample 60-day stress-cap result is not confirmed by walk-forward.
- Capped-decision rates are still high: about 70% for the best-looking 60-day variants.
- 120-day variants are more stable in OOS drawdown but cut too much annual return.
- This looks like a risk-control overlay, not a durable alpha improvement.

## Decision

Status:

- Simulation-ready: no
- Paper-ready: no
- Market stress cap: risk-control candidate only, not a profit-factor discovery.

Direction change:

- Do not keep tuning market-regime caps this round.
- Keep `entry_cash_no_overlay`, `vol_target_5_lb84`, and `vol_target_4_lb168` as benchmark/wrapper candidates.
- Return the main mining effort to the stock-selection factor itself, preferably public-method-inspired cross-sectional families with PIT and capacity controls.
