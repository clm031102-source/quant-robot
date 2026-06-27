# CN Stock Rounds363-365 Three-Round Audit

Date: 2026-06-27

Machine/task: `office_desktop` / `factor_validation`

Safety boundary: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Rounds Reviewed

| Round | Work | Useful Output | Decision |
| ---: | --- | --- | --- |
| 363 | Added simulation shortlist event-schema replay | All 5 packaged shortlist candidates pass metric replay plus event structure checks | Make replay mandatory before simulation handoff |
| 364 | Tested public indicators as second-stage filters inside `primary_low10` replacement basket | ADX bottom20 cash filter improved drawdown and overlap in full sample | Treat as defensive research lead only |
| 365 | Ran fixed rolling OOS split for ADX filter vs current shortlist | ADX 50% improves worst OOS drawdown but does not beat primary defensive on OOS return/overlap | Do not add to simulation shortlist yet |

## What Worked

The work corrected a real workflow weakness:

- before Round363, shortlist evidence could match metrics while still hiding event-column mistakes;
- after Round363, missing `decision_date`, missing `final_exposure`, mismatched `riskoff_multiplier`, and bad date ordering are blocked.

The public-indicator work also moved in the right direction:

- it did not rerun public indicators as standalone alpha after Round265 failure;
- it tested them only as risk filters inside the existing useful low-turnover replacement basket;
- it reproduced the official 834-date event calendar before trusting the result;
- it stopped after OOS showed the ADX filter was not dominant.

## Best New Research Lead

`public_adx_trend_strength_exhaustion_reversal_14_20_cash_bottom20_on_primary_low10 + vol_target_6_lb84 + zz500_mult_0.50`

Full sample:

- annualized return: 5.34%;
- Sharpe: 1.050;
- overlap Sharpe: 0.565;
- max drawdown: -16.87%;
- leave-one-year minimum annualized return: 3.20%;
- leave-one-year minimum overlap Sharpe: 0.501.

OOS split:

- mean OOS annualized return: 5.43%;
- minimum OOS annualized return: -5.27%;
- mean OOS overlap: 0.676;
- worst OOS drawdown: -9.11%;
- strict pass rate: 88.46%.

## Why It Is Not Promoted

It does not dominate `primary_defensive_zz500_50`:

- OOS annualized return is lower: 5.43% vs 5.62%;
- OOS overlap is lower: 0.676 vs 0.686;
- the improvement is mainly drawdown reduction.

It also does not dominate `primary_ps_filtered_defensive_zz500` as a pure defensive lane:

- PS has better OOS overlap and slightly lower worst OOS drawdown;
- ADX has better OOS annualized return and strict pass rate.

So ADX is a useful comparison candidate, not a replacement.

## Direction Decision

Stop broad public-indicator sweeps.

Allowed next actions:

1. Keep the existing five simulation shortlist candidates unchanged.
2. Keep ADX bottom20 as a defensive research lead, not shortlist.
3. If revisiting ADX, only run cost/beta and event-schema packaging; do not search ADX/SuperTrend/MACD/RSI parameters.
4. Return mining budget to more orthogonal sources: industry/board neutralization, event timing, breadth/regime translation, or financial-reporting timeliness once source coverage is adequate.

## Process Update

Every future shortlist candidate must pass:

- metric replay;
- event-schema replay;
- block-dependence audit;
- fixed OOS split;
- cost/beta quickcheck;
- no final-holdout access before explicit final validation.
