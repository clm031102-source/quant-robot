# CN Stock Round340-342 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Rounds Reviewed

| Round | Work | Status |
|---:|---|---|
| 340 | Candidate comparison pack | Completed |
| 341 | `turnover_rate_f` threshold sensitivity | Completed |
| 342 | Trade capacity stress tool and report | Completed |

## Main Finding

The current best line is not a one-row artifact.

Primary candidate:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

Evidence:

- full-sample total return: +177.08%;
- annualized return: +6.35%;
- Sharpe: 0.960;
- overlap-adjusted Sharpe: 0.517;
- max drawdown: -28.88%;
- mean OOS annualized return across split schemes: +7.24%;
- mean OOS overlap Sharpe: 0.688;
- no capacity breach through 20x the 1,000,000 research notional.

## What Improved

Round340 packaged the best candidates into a comparable table instead of continuing to chase isolated leaderboards.

Round341 showed threshold robustness:

- 5%, 10%, and 15% `turnover_rate_f` replacement exclusions form a plateau;
- 10% remains the best balanced default;
- 5% is the safer research variant;
- 15% has stronger OOS but breaches the approximate 30% full-sample drawdown tolerance.

Round342 added a reusable capacity tool:

`scripts/run_trade_capacity_stress.py`

This is now available for future candidate checks before simulation or paper-review packaging.

## Not Yet Solved

The dominant unsolved risk is still 2017-2018.

For the primary candidate:

- 2017-2018 annualized return: -6.86%;
- 2017-2018 max drawdown: -28.88%;
- 2019-2025 periods are all positive in the current regime audit.

The factor looks like a tradable low-turnover/dead-liquidity repair, not a universal all-regime alpha. It should not be promoted as a standalone always-on live signal without regime controls.

## Direction Audit

This direction is no longer blind factor mining. It is a failure-repair path:

1. identify the prior profitable but fragile `turnover_rate_low` lead;
2. isolate its loss pocket;
3. remove or replace the specific stale free-float turnover tail;
4. add volatility targeting only after fixing calendar alignment;
5. test threshold sensitivity and capacity.

That is the right shape of work for the 24h objective.

The next work should not add more random public indicators to this same candidate. Round336 already showed direct public cash filters did not beat the simpler `turnover_rate_f` repair.

## Updated Plan

Next priority:

1. attack 2017-2018 regime loss directly;
2. test simple, predeclared regime guards that do not optimize on the final holdout;
3. keep the current candidate frozen as the benchmark;
4. compare every new wrapper against both the safer cash benchmark and the primary replacement candidate;
5. keep 2026 sealed until a read-once final validation.

Accepted candidate set for the next round:

- default: `replace_drop_turnover_f_low10 + vol_target_6_lb84`;
- safer threshold: `replace_drop_turnover_f_low05 + vol_target_6_lb84`;
- aggressive research threshold: `replace_drop_turnover_f_low15 + vol_target_6_lb84`;
- safer benchmark: `cash_low_turnover_f_bottom20 + vol_target_5_lb84`.

Rejected or de-prioritized:

- direct public-indicator cash filters from Round336;
- 20% turnover-f threshold;
- aggressive low20-or-PB as simulation default because full-sample drawdown exceeds 30%.
