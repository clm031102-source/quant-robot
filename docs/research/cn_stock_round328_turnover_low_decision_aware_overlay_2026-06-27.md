# CN Stock Round328 Turnover-Low Decision-Aware Overlay

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock low-turnover research lead.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Why This Round Exists

Round323-324 fixed market-state overlay alignment by using `signal_date` or `entry_date` instead of exit date. During the next review, a second timing issue was found:

- The drawdown and volatility overlays were still driven by a period-return series indexed by exit date.
- That can let a signal-day risk decision indirectly use trade outcomes that are only known after the signal date.
- This is a potential future-function problem for any stateful overlay, even if the market-state cap itself is decision-date aligned.

Round328 adds a decision-aware event replay:

1. Each period-return row keeps `date` as the return realization or exit date.
2. Each row also keeps `decision_date` from `signal_date`.
3. Exposure is decided on `decision_date`.
4. The overlay state can only use returns from rows whose exit date is already closed before that decision date.
5. The adjusted return is then booked on the exit date.

New regression test:

- `test_period_event_drawdown_overlay_uses_only_returns_closed_before_decision_date`

## Output

Output directory:

`data/reports/round328_24h_profit_sprint_turnover_low_decision_aware_overlay_grid_20260627`

Main generated files:

- `turnover_low_overlay_walk_forward_policy_summary.csv`
- `turnover_low_overlay_walk_forward_selected_by_train.csv`
- `turnover_low_overlay_full_sample_policy_summary.csv`

## Walk-Forward Result

Configuration:

- Base return: `entry_cash_proxy_return`
- Decision date: `signal_date`
- Train/test: 3 years / 1 year / 1 year step
- Holding period: 20 trading days
- Periods per year: 252 / 5
- Policy count: 59
- Market caps: lagged clean-universe median market state caps

Best fixed policies by average test overlap-adjusted Sharpe:

| Policy | Avg Test Ann | Avg Test Sharpe | Avg Test Overlap | Worst Test DD | Positive Test | Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `vol_target_6_lb21` | +4.71% | 0.644 | 0.380 | -19.74% | 85.71% | 71.43% |
| `dd_warn15%_cut25%_exp50_25` | +4.71% | 0.578 | 0.379 | -18.18% | 85.71% | 85.71% |
| `vol_target_6_lb63` | +4.75% | 0.656 | 0.378 | -19.98% | 85.71% | 71.43% |
| `vol_target_8_lb21` | +4.81% | 0.644 | 0.377 | -19.97% | 85.71% | 85.71% |
| `entry_cash_no_overlay` | +4.64% | 0.622 | 0.365 | -19.97% | 85.71% | 85.71% |

Train-selected policy mix:

- 7 folds
- selected average test annualized return: +5.35%
- selected average test Sharpe: 0.595
- selected average test overlap-adjusted Sharpe: 0.337
- selected worst test drawdown: -10.75%
- selected strict pass rate: 71.43%

The selected-by-train stream still had one bad OOS fold:

- 2018-01-09 to 2019-01-08 selected `dd15_cut25_market_lb120_mom0_dd0p1_cap0p25`
- test annualized return: -3.64%
- test Sharpe: -2.776
- test overlap-adjusted Sharpe: -2.183
- test max drawdown: -5.39%

## Full-Sample Fixed-Policy Check

This is not used as promotion evidence by itself. It is a long-cycle sanity check for fixed policies from the same grid.

| Policy | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Avg Exposure |
|---|---:|---:|---:|---:|---:|---:|
| `vol_target_6_lb126` | +131.83% | +5.21% | 0.795 | 0.433 | -27.13% | 89.84% |
| `vol_target_6_lb63` | +129.24% | +5.14% | 0.810 | 0.429 | -27.99% | 89.15% |
| `vol_target_8_lb126` | +126.13% | +5.05% | 0.743 | 0.409 | -29.67% | 94.86% |
| `vol_target_8_lb63` | +124.16% | +5.00% | 0.747 | 0.404 | -30.25% | 95.36% |
| `entry_cash_no_overlay` | +107.64% | +4.51% | 0.644 | 0.355 | -35.63% | 100.00% |

## Interpretation

The useful object is not a new raw stock-selection factor. It is a stricter portfolio-construction wrapper around the existing low-turnover lead:

- `turnover_rate_low` remains the stock-selection source.
- `entry_cash_proxy_return` remains the tradeability-aware return stream.
- `vol_target_6_lb63` and `vol_target_6_lb126` are the most interesting fixed-policy candidates because they improve full-sample Sharpe and overlap Sharpe while keeping max drawdown near or below 30%.
- `dd_warn15%_cut25%_exp50_25` is the most robust simple drawdown policy in walk-forward strict pass rate, but it cuts full-sample total return too much.

Current best research lead:

`turnover_rate_low + entry-cash tradeability handling + decision-aware volatility targeting`

Preferred parameter candidates for the next validation block:

- `vol_target_6_lb63`
- `vol_target_6_lb126`
- `vol_target_8_lb126`
- benchmark: `entry_cash_no_overlay`

## Promotion Stance

Simulation-ready: no.

Paper-ready: no.

Reasons:

- One OOS fold remains negative.
- The policy grid is still a multiple-testing exercise.
- Full-sample `vol_target_6_lb126` is encouraging but was observed after grid expansion.
- The overlay is based on closed period returns, not a full daily mark-to-market portfolio engine.
- No independent final holdout or live-paper replay has been run.

This line is worth continuing because it is the first recent result with:

- full 2015-2025 sample;
- corrected decision-date overlay state;
- positive walk-forward average returns;
- drawdown around the user's acceptable range;
- stronger full-sample overlap Sharpe than the unwrapped low-turnover candidate.
