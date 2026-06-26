# CN Stock Round260 Official Tradeability Event Residual Prescreen

Date: 2026-06-26

Machine: office_desktop

Branch: codex/factor-validation-cn-stock-long-cycle-20260618

Stage: residual prescreen, research-to-review only

## Direction

Round260 implemented one of the pending optimization areas: real A-share tradeability and event-state controls. The family used the official 2015-2025 tradeability mask cache, not the old proxy limit-event line, and tested whether limit-up/down, suspension reopen, ST status, and clean tradeability state contain residual cross-sectional alpha after industry/style controls.

This was the right kind of direction to test because it is grounded in market microstructure, execution constraints, and real tradability. It was also intentionally different from the failed daily-basic, forecast, listing-age, public-reference, and moneyflow families.

## Candidates

Seven pre-registered factors were evaluated on 5-day and 20-day horizons:

- official_limit_down_reopen_rebound_5
- official_limit_up_crowding_avoidance_3
- official_limit_down_pressure_avoidance_5
- official_post_suspension_reopen_risk_avoidance_10
- official_st_name_risk_avoidance_20
- official_tradeability_cleanliness_20
- official_limit_state_recovery_quality_5

Candidate plan gate passed with all eight control areas present. No portfolio grid, promotion, final holdout, or live trading step was allowed at this stage.

## Full-Sample Evidence

The full core run covered 2015-01-01 to 2025-12-31 with both historical CN stock bar roots and the official tradeability mask root.

| Metric | Value |
|---|---:|
| Candidates | 7 |
| Horizon tests | 14 |
| Asset count | 5,707 |
| Bar rows | 10,785,537 |
| Factor rows | 70,773,554 |
| Industry-neutral rows | 70,758,796 |
| Residual rows | 70,194,236 |
| Label rows | 21,442,336 |
| Residual research leads | 0 |
| Portfolio preflight candidates | 0 |
| Promotion allowed candidates | 0 |

The 2024Q1 smoke run produced four provisional leads, but the long-cycle full core run rejected all of them. This is a useful failure: it confirms that short-window event-state signals are not enough evidence for portfolio work.

## Best Diagnostics

| Factor | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | t | Pos IC | Year Fail | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| official_st_name_risk_avoidance_20 | 20 | -0.0062 | -0.0075 | 0.0279 | 0.259 | 13.279 | 0.6189 | 3 | reject as tradeable alpha |
| official_st_name_risk_avoidance_20 | 5 | -0.0025 | -0.0032 | 0.0163 | 0.166 | 8.526 | 0.5880 | 2 | reject |
| official_limit_down_reopen_rebound_5 | 20 | 0.0405 | 0.0205 | 0.0106 | 0.172 | 8.807 | 0.6220 | 3 | reject |
| official_tradeability_cleanliness_20 | 20 | 0.0381 | 0.0199 | 0.0096 | 0.156 | 8.009 | 0.6144 | 3 | reject |
| official_limit_up_crowding_avoidance_3 | 20 | 0.0627 | 0.0071 | -0.0319 | -0.342 | -17.553 | 0.3507 | 10 | reject |

The important nuance is `official_st_name_risk_avoidance_20`: it has a positive residual IC above 0.02, but raw and industry-neutral IC are negative, ICIR is only 0.259, and yearly stability fails. That makes it more suitable as a risk/control variable than as a direct long-only alpha factor.

## Failure Analysis

The family failed for three reasons:

1. Raw event effects did not survive neutralization. Several signals looked strong before industry/style residualization, then collapsed or inverted after controls.
2. Positive diagnostics were not stable enough across years. The blocker was not just drawdown tolerance; the IC time series itself was not robust enough for portfolio preflight.
3. The event-state variables describe tradeability risk better than persistent return forecasting power. They should remain in the control and execution layer, not be expanded as a standalone alpha family.

## Process Decision

Official tradeability event-state factors are hibernated after Round260. Do not tune event windows, flip signs, run TopN portfolios, or run reference dedup/walk-forward from this family because there were zero full-sample residual research leads.

Round261 must rotate to a new orthogonal family. A good next family should come from one of the remaining optimization gaps, preferably a non-daily-basic, non-forecast direction with stronger economic rationale and clearer PIT timing, such as event revision with external expectation data, industry relative breadth/dispersion, or regime-conditional factor translation. Final holdout remains blocked.

