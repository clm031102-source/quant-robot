# CN Stock Round430 Extreme Trade Repair Profile

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round430 turns the Round428 extreme-trade warning into a repeatable process:

1. rebuild the current cohort-entry-timed default with trade-level final rows;
2. profile extreme active trades by entry-known attributes;
3. test a small set of repair candidates driven by the profile rather than blind parameter search.

## Reusable Tooling Added

Updated:

- `src/quant_robot/ops/simulation_shortlist_cohort_entry_timed.py`
  - now writes `cohort_trade_rows.csv`;
  - each trade row includes `entry_tilt_multiplier`, `dragon_cash_filter`, `public_factor_tilt`, `final_exposure`, `final_target_weight`, and `final_return_contribution`.

New:

- `src/quant_robot/ops/shortlist_extreme_trade_profile.py`
- `scripts/run_shortlist_extreme_trade_profile.py`
- `tests/unit/test_shortlist_extreme_trade_profile.py`
- `tests/unit/test_shortlist_extreme_trade_profile_cli.py`

This makes extreme-trade diagnosis repeatable for future candidates.

## Rebuild Check

Output:

`data/reports/round430_24h_profit_sprint_default_cohort_trade_profile_rebuild_20260627`

The rebuilt default exactly matches the Round425 default metrics:

| Candidate | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Win Rate |
|---|---:|---:|---:|---:|---:|---:|
| rebuilt default | 5.759% | +163.48% | 0.863 | 0.466 | -29.18% | 40.71% |

This confirms the trade-level output did not change candidate behavior.

## Extreme Profile

All active rows profile:

`data/reports/round430_24h_profit_sprint_default_cohort_extreme_trade_profile_20260627`

Contributing active rows profile:

`data/reports/round430_24h_profit_sprint_default_cohort_contributing_extreme_trade_profile_20260627`

Key contributing-trade findings:

| Metric | Default |
|---|---:|
| contributing active trades | 20,131 |
| contributing extreme trades, `abs(gross_return) > 50%` | 113 |
| extreme trade rate | 0.561% |
| extreme contribution sum | +40.92 percentage points |
| max contributing abs gross return | 255.55% |

High-risk entry-known or execution-known buckets:

| Bucket | Extreme Count | Extreme Rate | Lift |
|---|---:|---:|---:|
| `fully_tradeable_roundtrip=False` | 11 | 5.16% | 9.20x |
| `exit_allowed=False` | 11 | 5.16% | 9.20x |
| `public_factor_tilt=True` | 27 | 1.49% | 2.65x |
| industry `半导体` | 5 | 3.68% | 6.55x |
| industry `超市连锁` | 5 | 3.36% | 5.98x |
| industry `玻璃` | 5 | 2.09% | 3.73x |
| industry `电气设备` | 7 | 1.30% | 2.31x |

Numeric profile:

- extreme trades have higher `turnover_rate_f`: mean 3.68 vs 1.99;
- extreme trades have higher `pb`: mean 6.30 vs 2.75;
- extreme trades have higher `entry_amount`: mean 383.4M vs 190.2M;
- extreme trades do not have higher participation rate.

Interpretation:

The main repair target is not raw capacity. It is exit-tradeability treatment plus high-turnover/high-PB/public-tilt tail exposure.

## Repair Screen

Tested candidates:

| Candidate | Change | Annualized | Total Return | Overlap Sharpe | Max DD | Best Month Share |
|---|---|---:|---:|---:|---:|---:|
| default | entry-cash proxy, 1.50x tilt | 5.759% | +163.48% | 0.466 | -29.18% | 48.00% |
| `tilt_m125` | entry-cash proxy, 1.25x tilt | 5.402% | +148.50% | 0.450 | -29.58% | 49.83% |
| `tilt_m100` | entry-cash proxy, 1.00x tilt | 5.061% | +134.93% | 0.434 | -30.16% | 51.75% |
| `roundtrip_m150` | roundtrip cash proxy, 1.50x tilt | 5.832% | +166.65% | 0.486 | -25.98% | 46.35% |
| `roundtrip_m125` | roundtrip cash proxy, 1.25x tilt | 5.475% | +151.50% | 0.470 | -26.43% | 48.09% |

Lowering the public-factor multiplier alone is not a good repair. It reduces return and does not improve drawdown enough.

The roundtrip cash-proxy repair is materially better in full sample, but it must be interpreted carefully.

## OOS And Beta Checks

OOS:

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| default | 8.533% | 0.881 | -20.94% | 90.00% |
| `roundtrip_m150` | 8.369% | 0.873 | -19.46% | 90.00% |
| `tilt_m125` | 8.075% | 0.859 | -20.51% | 90.00% |
| `roundtrip_m125` | 7.907% | 0.848 | -19.15% | 90.00% |
| `tilt_m100` | 7.666% | 0.838 | -20.13% | 90.00% |

Beta:

| Candidate | ZZ500 Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged Max DD | Alpha t |
|---|---:|---:|---:|---:|---:|---:|
| `roundtrip_m150` | 0.0460 | 0.278 | 6.264% | 0.778 | -13.55% | 3.93 |
| default | 0.0474 | 0.285 | 6.234% | 0.752 | -15.10% | 3.87 |
| `roundtrip_m125` | 0.0450 | 0.280 | 5.853% | 0.753 | -13.53% | 3.78 |
| `tilt_m125` | 0.0465 | 0.287 | 5.818% | 0.728 | -15.08% | 3.71 |

## Roundtrip Profile After Repair

Output:

`data/reports/round430_24h_profit_sprint_roundtrip_m150_contributing_extreme_trade_profile_20260627`

| Metric | Default | Roundtrip m150 |
|---|---:|---:|
| contributing active trades | 20,131 | 19,918 |
| contributing extreme trades | 113 | 102 |
| extreme trade rate | 0.561% | 0.512% |
| extreme contribution sum | +40.92 pp | +36.79 pp |
| max contributing abs gross return | 255.55% | 254.02% |
| negative extreme count | 4 | 1 |

The exit-tradeability risk bucket is removed from the main risk-candidate list. Remaining risk buckets are public tilt and a few small industry buckets, plus higher `turnover_rate_f` and `pb`.

## Decision

Do not promote `tilt_m125` or `tilt_m100`.

Upgrade `roundtrip_m150` to the best execution-stress research candidate, not a clean paper-simulation handoff yet.

Reason:

- It improves full-sample return, drawdown, overlap Sharpe, and beta-hedged profile.
- OOS is slightly weaker than default but still has 90% strict pass.
- It reduces the real contributing extreme-trade count and extreme contribution.
- But `roundtrip_cash_proxy_weighted_return` uses exit-date tradeability, so it is not an entry-known factor. It is a conservative execution-stress return stream, not a deployable entry rule.

## Next Direction

The next required work is a causal execution repair:

1. implement or run delayed-exit simulation when exit is blocked, rather than using future exit information as an entry filter;
2. test entry-known high-turnover/high-PB risk budgets for public-tilt trades;
3. retest the surviving candidate with OOS, beta, cost, block dependence, and the extreme profile;
4. only then decide whether the simulation handoff should switch from the Round425 default to the Round430 repaired stream.
