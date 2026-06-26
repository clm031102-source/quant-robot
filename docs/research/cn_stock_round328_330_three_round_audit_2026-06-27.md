# CN Stock Round328-330 Three-Round Audit

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock factor validation.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Rounds Covered

| Round | Purpose | Main Output | Decision |
|---|---|---|---|
| 328 | Fix stateful overlay timing bug | Decision-aware period-event replay | Prior stateful overlay evidence before Round328 is superseded |
| 329 | Vol-target sensitivity | Broad target/lookback plateau found | Freeze simple candidates; stop rolling train-selected tuning |
| 330 | Fixed-candidate robustness | Cross-split, full sample, yearly and subperiod risk | Continue only with ex-ante market-state cap test |

## What Improved

Round328 materially improved research validity:

- Overlay exposure is decided on `signal_date`.
- Overlay state only uses returns whose exit date is already closed before that decision date.
- Adjusted returns are booked on exit date.
- A regression test blocks the previous future-function pattern.

Round329 reduced parameter-mining risk:

- Volatility target results were a broad plateau, not one isolated lucky point.
- Rolling train-selected policy choice underperformed fixed policies.
- This is evidence to freeze policies rather than keep optimizing parameters.

Round330 identified the key failure regime:

- 2017-2018 deleveraging remains the main loss source.
- 2018 losses are nearly identical across no-overlay and vol-target overlays.
- Realized strategy volatility targeting reacts too late when the regime shift happens before closed strategy returns have deteriorated enough.

## Best Evidence So Far

Best full-sample diagnostic:

- `vol_target_5_lb84`
- total return: +145.41%
- annualized return: +5.58%
- Sharpe: 0.904
- overlap-adjusted Sharpe: 0.483
- max drawdown: -26.95%

Best cross-split robustness:

- `vol_target_4_lb168`
- mean OOS annualized return: +6.02%
- minimum OOS annualized return across tested split types: +3.77%
- mean OOS overlap-adjusted Sharpe: 0.573
- worst OOS drawdown: -19.97%
- mean strict pass rate: 90.18%

Important negative evidence:

- All policies lost about 20% in 2018.
- The worst subperiod remains 2017-2018, with annualized return around -6.5% and overlap-adjusted Sharpe near -1.1.
- The no-overlay benchmark remains competitive OOS, so the overlay has not yet proven a strong independent edge.

## Promotion Decision

No factor or policy is promotable yet.

Current status:

- Simulation-ready: 0
- Paper-ready: 0
- Research leads worth continuing: 1

Active research lead:

`turnover_rate_low + entry-cash tradeability handling + decision-aware volatility targeting`

But it must now pass an ex-ante market-state cap test before more time is spent on this family.

## Direction Adjustment

Stop doing:

- Same-family low-turnover parameter sweeps.
- Rolling train-selected volatility target parameters.
- Treating full-sample return as promotion evidence.

Start doing:

- Use fixed candidates only.
- Layer a simple market regime cap known at decision date.
- Prioritize 2017-2018 and 2015 crash behavior over full-sample ranking.
- Preserve 2026 as final holdout.

Next round should test:

1. `vol_target_4_lb168 + market_state_cap`
2. `vol_target_5_lb84 + market_state_cap`
3. `vol_target_7_lb63 + market_state_cap`
4. `entry_cash_no_overlay + market_state_cap`

The market-state cap must be ex-ante:

- based on clean-universe median market returns;
- computed with lagged market momentum and drawdown;
- aligned by `signal_date`;
- fixed before reading results.
