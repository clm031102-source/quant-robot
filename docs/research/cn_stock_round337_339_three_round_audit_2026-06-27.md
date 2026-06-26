# CN Stock Round337-339 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Rounds Audited

| Round | Direction | Outcome |
|---:|---|---|
| 337 | Replacement filters without cashing | Invalid as evidence because data quarantine was not applied |
| 338 | Quarantine-corrected replacement filters | Useful new direction; return and OOS overlap improved but drawdown remained high |
| 339 | Replacement filters with vol-target wrappers | Produced the current best balanced research candidate |

## Data-Quality Audit

Round337 is not valid promotion evidence.

Root cause:

- it omitted Round322/Round333 quarantine;
- candidate universe expanded beyond the validated 1,749-asset clean universe;
- first-date selected assets changed;
- results cannot be compared to previous rounds.

Round338 fixed this. Its `replace_no_extra_filter` reproduced Round322/Round333 exactly:

- total return: +107.64%;
- annualized return: +4.51%;
- max drawdown: -35.63%;
- absolute date-return diff versus Round322: effectively zero.

## What Worked

Replacement construction worked better than cash-only filtering.

The best corrected replacement rows improved OOS return and overlap, but the aggressive versions still had full-sample drawdown around 40%.

Round339 showed that applying a decision-aware volatility wrapper can make the conservative replacement candidate more balanced.

## Current Candidates

### Balanced Candidate

`replace_drop_turnover_f_low10 + vol_target_6_lb84`

Full sample:

- total return: +177.08%;
- annualized return: +6.35%;
- Sharpe: 0.960;
- overlap Sharpe: 0.517;
- max drawdown: -28.88%;
- average exposure: 89.15%.

Cross-split:

- mean OOS annualized return: +7.24%;
- min OOS annualized return: +4.83%;
- mean OOS overlap Sharpe: 0.688;
- worst OOS drawdown: -20.10%;
- strict pass rate: 74.32%.

### Safer Benchmark

`cash_low_turnover_f_bottom20 + vol_target_5_lb84`

Full sample:

- total return: +137.10%;
- annualized return: +5.36%;
- Sharpe: 0.984;
- overlap Sharpe: 0.533;
- max drawdown: -21.98%;
- average exposure: 90.35%.

Cross-split:

- mean OOS annualized return: +5.53%;
- min OOS annualized return: +3.60%;
- mean OOS overlap Sharpe: 0.639;
- worst OOS drawdown: -16.13%;
- strict pass rate: 74.32%.

### Aggressive Research Candidate

`replace_drop_turnover_f_low20_or_pb_high20 + vol_target_5_lb84`

Full sample:

- total return: +168.73%;
- annualized return: +6.16%;
- Sharpe: 0.953;
- overlap Sharpe: 0.514;
- max drawdown: -31.83%.

It has stronger OOS than `low10`, but full-sample drawdown exceeds the current 30% comfort line. Keep as research-only.

## Remaining Problem

The 2017-2018 regime remains the main unresolved weakness.

For `replace_drop_turnover_f_low10 + vol_target_6_lb84`:

- 2017-2018 annualized return: -6.86%;
- 2017-2018 max drawdown: -28.88%;
- 2018 annualized return: -10.66%.

This is tolerable under a loose drawdown budget, but it is not a solved crisis regime.

## Direction After Audit

Do not keep broad-searching public indicators.

Do not trust any replacement result unless it reproduces the quarantine baseline.

Next work should be:

1. final promotion-style comparison of balanced candidate vs safer benchmark;
2. capacity and tradeability summary for both;
3. sensitivity around the `turnover_rate_f` exclusion threshold, but only 5/10/15/20, not wide tuning;
4. no 2026 holdout use until final read-once validation.
