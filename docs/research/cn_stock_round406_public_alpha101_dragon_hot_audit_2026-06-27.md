# CN Stock Round406 - Public Alpha101 Dragon-Hot Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round406 audited the strongest Round405 public Alpha101 filters/tilts after applying the same vt6 and ZZ500 risk-off wrapper schema used in Round384.

This keeps comparisons fair against `dragon_hot_100`, Qlib tilt, and Qlib self-risk observations.

## Outputs

- Wrapper: `data/reports/round406_24h_profit_sprint_public_alpha101_dragon_hot_wrapper_audit_20260627`
- OOS: `data/reports/round406_24h_profit_sprint_public_alpha101_dragon_hot_oos_20260627`
- Block audit: `data/reports/round406_24h_profit_sprint_public_alpha101_dragon_hot_block_audit_20260627`
- Beta audit: `data/reports/round406_24h_profit_sprint_public_alpha101_dragon_hot_beta_audit_20260627`

## Best High-Return Observation

`tilt_a101_open_close_bottom10_m150_vt6_zz500_mult_1.00`

- total return: +216.69%
- annualized return: 7.21%
- Sharpe: 1.035
- overlap Sharpe: 0.558
- max drawdown: -29.84%
- win rate: 40.65%
- leave-one-year min annualized return: 4.50%
- best-month log share: 0.428
- mean OOS annualized return: 8.82%
- mean OOS overlap Sharpe: 0.914
- worst OOS drawdown: -24.58%
- strict OOS pass rate: 90%
- ZZ500 beta: 0.0420
- beta-hedged annualized return: 7.18%
- beta-hedged overlap Sharpe: 0.886
- beta-hedged max drawdown: -14.05%

Interpretation: this is now one of the strongest high-return observations, but its full-sample drawdown is close to the user's 30% tolerance. It should enter simulation as aggressive, not default.

## Best Balanced Observation

`cash_a101_open_close_top10_vt6_zz500_mult_0.75`

- total return: +166.31%
- annualized return: 6.10%
- Sharpe: 1.124
- overlap Sharpe: 0.607
- max drawdown: -22.07%
- win rate: 41.49%
- leave-one-year min annualized return: 3.76%
- best-month log share: 0.401
- mean OOS annualized return: 7.10%
- mean OOS overlap Sharpe: 0.962
- worst OOS drawdown: -16.68%
- strict OOS pass rate: 90%
- ZZ500 beta: 0.0323
- beta-hedged annualized return: 6.06%
- beta-hedged overlap Sharpe: 0.998
- beta-hedged max drawdown: -11.27%

Interpretation: lower return than the aggressive tilt, but much cleaner drawdown and beta-hedged shape. This is the better balanced simulation comparison lane.

## Decision

Add two observations to the simulation shortlist:

- `primary_high_return_dragon_hot_chase_alpha101_openclose_bottom10_tilt_m150`
- `primary_balanced_dragon_hot_chase_alpha101_openclose_top10_cash_zz500075`

Promotion allowed: false. These are simulation candidates, not final paper/live signals.
