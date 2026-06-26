# CN Stock Calendar Seasonality Preregistration Round163

## Executive Summary

- Machine/task context: `office_desktop`, `factor_validation`, CN stock factor mining.
- Source audit: `docs/research/cn_stock_round160_162_three_round_review_2026-06-23.md`.
- Negative evidence: Round160 tradeability/limit-event proxy prescreen produced zero proxy research leads; Round162 market-regime-temperature residual prescreen produced zero residual research leads.
- Decision: rotate away from the failed recent families and pre-register an ex-ante calendar-seasonality family.
- Output: 8 candidate specs, 8 families, 0 failed-family re-entry candidates, 0 portfolio candidates, 0 promotion candidates.
- Next required gate: `round164_cn_calendar_seasonality_residual_prescreen`.

## Why This Direction

The recent failures were not just parameter failures; they were family-level evidence that moneyflow, tradeability/limit proxy events, public technical failure reversal, price-volume shock reversal, PIT event revision, lottery tails, low-turnover repair, daily-basic supply quality, and market-regime temperature should not receive more blind parameter sweeps. Round163 therefore moves to a different public anomaly class: known calendar states that are observable before the signal date.

The core research question is narrow: do month-turn, month-end, month-start, pre/post-holiday, weekday, or quarter-end windows improve residual cross-sectional stock signals after tradeability, industry/style, coverage, 2015 stress, and multiple-testing controls?

## Required Controls

- `ex_ante_calendar_state`: the calendar state must be known before signal generation.
- `cn_trading_calendar_alignment`: windows must use the CN trading calendar, not naive calendar days.
- `no_future_holiday_gap_lookup`: holiday-window construction cannot inspect future returns or future signal outcomes.
- `tradeability_filter_before_signal`: blocked or non-tradable names must not be selected by the signal.
- `industry_style_residual_evaluation`: raw IC is insufficient; residual IC is the gate.
- `calendar_bucket_coverage`: sparse calendar buckets cannot be treated as stable evidence.
- `yearly_and_2015_stress_breakout`: 2015 must be separated, not hidden inside the full-sample mean.
- `multiple_testing_accounting`: all 8 hypotheses count.
- `no_portfolio_grid_before_residual_prescreen`: no TopN/cost grid until residual prescreen clears.

## Candidate Specs

| Factor | Family | Direction | Windows | Thesis |
|---|---|---:|---:|---|
| `turn_of_month_reversal_liquid_5_5` | turn_of_month_reversal | higher | 5,20 | Month-turn liquidity and rebalance flows may improve liquid short-term reversal. |
| `turn_of_month_residual_momentum_20_5` | turn_of_month_momentum | higher | 5,20,60 | Residual momentum may be paid only near the month turn after beta control. |
| `month_end_crowding_exhaustion_10_5` | month_end_exhaustion | lower | 5,10,20 | Hot winners near month end may fade after crowding/rebalance pressure. |
| `month_start_liquidity_recovery_5_5` | month_start_liquidity_recovery | higher | 5,20 | Beginning-of-month liquidity normalization may help liquid low-vol rebound names. |
| `pre_holiday_liquidity_avoidance_5_3` | pre_holiday_liquidity_avoidance | lower | 3,5,20 | Crowded strength before known holidays may be fragile as liquidity thins. |
| `post_holiday_gap_reversal_quality_3_5` | post_holiday_reversal | higher | 3,5,20 | Post-holiday gap overreaction may reverse in cleaner, lower-vol names. |
| `weekday_monday_reversal_quality_5_5` | weekday_reversal | higher | 5,20 | Monday may expose behavioral reversal after weekend information digestion. |
| `quarter_end_liquidity_window_reversal_20_5` | quarter_end_liquidity_window | higher | 5,20,60 | Quarter-end liquidity/reporting pressure may create a reversal window. |

## Promotion Boundary

No factor from Round163 is useful yet in the trading sense. This round only corrected the direction and registered hypotheses. A candidate can become a research lead only after Round164 shows residual IC, yearly stability, calendar-bucket coverage, reference dedup, 2015 stress survival, and tradeability/cost preflight evidence.

## Next Step

Run `round164_cn_calendar_seasonality_residual_prescreen` on the long CN-stock sample. The prescreen should reject the whole family quickly if residual IC collapses into ordinary return, liquidity, low-volatility, size, or 2015-only exposure.
