# CN Stock Round163-165 Three-Round Review

Date: 2026-06-23

## Scope

This review satisfies the governance rule: every 3 rounds, audit the previous work and adjust the plan before continuing factor mining.

Reviewed rounds:

- Round163: calendar-seasonality preregistration
- Round164: calendar-seasonality residual prescreen
- Round165: pre-holiday cost/capacity preflight

## Outcomes

| Round | Work | Unique candidates | Useful leads | Portfolio candidates | Promotion candidates | Decision |
|---:|---|---:|---:|---:|---:|---|
| 163 | Calendar-seasonality preregistration | 8 | prereg only | 0 | 0 | Correctly rotated away from failed regime-temperature line |
| 164 | Residual IC, redundancy, exposure, and 2015 stress prescreen | 8 | 1 | 0 | 0 | Only `pre_holiday_liquidity_avoidance_5_3` survived as a research lead |
| 165 | Cost/capacity preflight for frozen pre-holiday lead | 1 factor, 12 cases | 0 tradable | 0 | 0 | All 12 cases hard-blocked; hibernate calendar family |

## What Improved

The process improved in four useful ways:

- The family rotation happened quickly after Round162 produced zero residual leads.
- Round163 froze 8 ex-ante calendar hypotheses before looking at portfolio returns.
- Round164 separated raw, industry-neutral, and residual IC, then checked reference redundancy, style exposure, calendar coverage, yearly stability, and 2015 stress.
- Round165 prevented a raw total-return trap: the best case had 48.29% total return, but only 2.85% annualized return and 0.443 overlap-adjusted Sharpe.

## Why Calendar Failed

The calendar family did not fail at preregistration or residual IC. It failed at the trading translation layer.

`pre_holiday_liquidity_avoidance_5_3` looked promising in Round164:

- residual mean IC: 0.0487
- residual ICIR: 0.6560
- residual IC positive rate: 74.29%
- yearly residual failure count: 0
- 2015 residual IC: 0.0488
- high reference redundancy count: 0
- high style exposure count: 0

But Round165 showed that this residual signal was not strong enough after execution constraints:

- best total return: 48.29%
- best annualized return: 2.85%
- best raw Sharpe: 0.594
- best overlap-adjusted Sharpe: 0.443
- best max drawdown: -10.66%
- best win rate: 55.1%
- cost/capital cases tested: 12
- hard-blocked cases: 12
- walk-forward candidates: 0

The failure is therefore not mainly drawdown. The user can tolerate larger drawdowns when return quality is strong, but this path failed because overlap-adjusted quality was too weak, event windows were sparse, calendar holding gates filtered trades, and capacity limits appeared before the signal had enough quality.

## Stop-Loss Decision

Hibernate `calendar_seasonality`.

Blocked next actions:

- tuning pre-holiday windows after Round165;
- sending `pre_holiday_liquidity_avoidance_5_3` to walk-forward after the cost/capacity failure;
- using total return alone as promotion evidence;
- using drawdown tolerance as a waiver for overlap-adjusted Sharpe, calendar holding, or capacity gates;
- continuing month-turn, post-holiday, weekday, or quarter-end variants without a genuinely new information source.

## Next Direction

Round166 should not be another price/volume/calendar formula family. The higher-value move is:

- `round166_external_macro_northbound_credit_data_feed_audit`

Reason: several better CN-stock hypotheses need information that is not currently proven in the local processed store: northbound participation, margin financing/short balance, index-location state, credit/liquidity cycle proxies, and macro/rates/commodity state. The startup gate already blocks `external_macro_or_northbound_credit_factor_before_data_feed_audit`; therefore the next round must audit local availability, point-in-time alignment, coverage, and integration cost before any factor formula is generated.

The output of Round166 should decide one of three paths:

- proceed to preregister a northbound/margin/regime family if local or Tushare-accessible data is clean enough;
- build a minimal ingestion plan if the endpoint exists but the project lacks processed history;
- reject the direction temporarily if data is unavailable, too sparse, or not point-in-time safe.

Portfolio and promotion remain blocked.

