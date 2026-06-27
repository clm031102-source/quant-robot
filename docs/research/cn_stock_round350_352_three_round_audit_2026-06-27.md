# CN Stock Round350-352 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

The standing target requires a review after every three rounds. This audit covers:

- Round350: CSI500 risk-off multiplier sensitivity;
- Round351: 75% risk-off cost/beta quickcheck;
- Round352: non-turnover daily-basic public anomaly clean-portfolio diagnostic.

2026 final holdout remains sealed.

## Round Decisions

| Round | Direction | Result | Decision |
|---|---|---|---|
| 350 | CSI500 risk-off multiplier 0/25/50/75/100 | 75% is a useful return/risk middle lane; 50% remains best defensive setting | Keep 50%, add 75% for observation |
| 351 | 75% cost/beta quickcheck | 75% survives current-cost and beta checks; 30 bps strict pass weaker than 50% | Add `primary_balanced_zz500_75`, but do not replace `primary_defensive_zz500` |
| 352 | Daily-basic public anomaly direct TopN | 0/48 diagnostic pass cases; best overlap Sharpe only 0.231 with -47.37% drawdown | Reject direct value/yield/public-anomaly TopN direction |

## What Improved

The simulation shortlist now has a more useful risk spectrum:

| Lane | Candidate | Total | Ann. | Overlap Sharpe | Max DD | Use |
|---|---|---:|---:|---:|---:|---|
| Return-seeking | `primary_high_return` | +177.08% | +6.35% | 0.517 | -28.88% | highest return, drawdown near user tolerance |
| Balanced observation | `primary_balanced_zz500_75` | +161.99% | +5.99% | 0.530 | -24.74% | middle lane added in this audit block |
| Defensive default | `primary_defensive_zz500` | +147.29% | +5.62% | 0.536 | -20.38% | stronger cost robustness |
| Low-drawdown reference | `safer_defensive_zz500` | +114.76% | +4.73% | 0.534 | -14.94% | benchmark/reference |

The new `primary_balanced_zz500_75` gives the user a better option if higher return matters more than the 50% defensive drawdown profile, while still reducing risk versus the 100% baseline.

## What Failed

Round352 is a clear negative result:

- daily-basic value/yield/carry factors did not pass diagnostic gates;
- best annualized return was only +4.04%;
- best overlap Sharpe was 0.231;
- best max drawdown was -47.37%;
- extreme-trade excluded metrics deteriorated sharply.

This says the project should not rotate into direct public anomaly TopN portfolios. The current useful signal is not "any daily-basic factor"; it is the more specific low-turnover/replacement/entry-cash/vol-target construction with external regime control.

## Direction Adjustment

Keep:

- current low-turnover replacement framework;
- 50% and 75% CSI500 risk-off overlays;
- cost/beta/capacity checks before promotion;
- sealed 2026 holdout.

Stop or hibernate:

- direct public technical indicator composites after Round265 zero residual leads;
- direct realized profitability-quality formulas after Round217/Round247 failures;
- forecast/express disagreement after Round268 zero leads;
- direct daily-basic public anomaly TopN after Round352 zero pass.

Next three-round block should not be another blind factor family sweep. It should prioritize one of:

- improve current candidate construction with official tradeability, loss-control, and ETF regime overlays;
- test value/yield/liquidity only as a secondary filter inside the already-useful low-turnover framework;
- resume a true PIT event/source only if there is enough local coverage and no provider-rate blocker.

## Current Conclusion

The useful output of this audit block is not a new standalone factor family. It is a better candidate stack:

- add `primary_balanced_zz500_75` to the simulation shortlist;
- keep `primary_defensive_zz500` as the robustness default;
- reject direct value/yield public anomaly portfolios.

This is directionally correct for the user's stated preference: allow larger drawdown when return improves, but do not accept weak Sharpe and uncontrolled -45% to -50% drawdowns from a lower-return family.
