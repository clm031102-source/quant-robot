# CN Stock Event Factor Preregistration Round146

- Date: 2026-06-22
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional factor mining, research-to-review only
- Source audit: `docs/research/cn_stock_daily_basic_free_float_supply_quality_final_holdout_round145_2026-06-22.md`

## Objective

Round145 proved that the daily-basic free-float supply quality line had 6 aggregate-accepted candidates but 0 final-holdout-passed candidates. Round146 therefore rotated to a new economic family instead of expanding failed parameters.

The selected family is announcement/event-driven A-share stock factors. This directly addresses a previous gap in the process: event factors such as earnings forecasts, dividends, buybacks, shareholder concentration, unlock pressure, and pledge pressure had not been made into a reusable preregistration gate.

## Live Endpoint Smoke

The Tushare token was present and used only through local scripts. The token was not printed or written.

Smoke command:

```powershell
python scripts\run_event_factor_preregistration.py --output-dir data\reports\event_factor_preregistration_round146_20260622
```

Endpoint probe result:

| Endpoint | Rows | Status |
| --- | ---: | --- |
| `dividend` | 266 | available |
| `forecast` | 6 | available |
| `repurchase` | 178 | available |
| `stk_holdernumber` | 84 | available |
| `top10_holders` | 149 | available |
| `top10_floatholders` | 101 | available |
| `express` | 0 | blocked for this sample |
| `share_float` | 0 | blocked for this sample |
| `pledge_stat` | 0 | blocked for this sample |

Summary:

- Event endpoints probed: 9
- Available endpoints: 6
- Pre-registered event candidates: 8
- Available candidates for next gate: 5
- Blocked candidates: 3
- Promotion allowed: false
- Portfolio backtest allowed before prescreen: false
- Next required gate: `round147_event_factor_pit_coverage_ic_prescreen_for_available_candidates`

## Cross-Section Query Feasibility

Round147 also probed whether the event endpoints can form real cross-sections instead of only single-stock samples.

| Query pattern | Endpoint | Rows | Cross-section ready |
| --- | --- | ---: | --- |
| `forecast_ann_date` | `forecast` | 2,210 | yes |
| `express_start_end` | `express` | 1,377 | yes |
| `dividend_ann_date` | `dividend` | 661 | yes |
| `dividend_end_date` | `dividend` | 2,000 | yes |
| `holdernumber_start_end` | `stk_holdernumber` | 5,500 | yes |
| `top10_holders_period` | `top10_holders` | 6,000 | yes |
| `top10_floatholders_period` | `top10_floatholders` | 6,000 | yes |
| `repurchase_ann_date_20250829` | `repurchase` | 49 | yes |
| `repurchase_ann_date_20240105` | `repurchase` | 15 | no, below the 30-row smoke threshold |

This is a meaningful upgrade over a pure single-symbol smoke. The available event family can proceed to real PIT cross-sectional IC work, provided each event date is converted to a tradable signal date and broad-history pulls are sharded and rate-limited.

## Available Candidates

These 5 candidates have at least smoke-level endpoint coverage and may proceed to a PIT coverage and IC prescreen. They are not profitability evidence yet.

| Factor | Family | Endpoint | Rationale |
| --- | --- | --- | --- |
| `event_forecast_profit_revision_1q` | earnings forecast | `forecast` | Profit forecast revisions test post-announcement drift with explicit `ann_date` timing. |
| `event_dividend_cash_yield_announced_1y` | dividend event | `dividend` | Cash dividend announcements test shareholder yield using real announcement/ex-date fields, not daily-basic proxy yield. |
| `event_repurchase_amount_to_mv_20` | buyback event | `repurchase` | Buyback amount scaled by market value tests undervaluation/shareholder-return intent. |
| `event_holder_number_contraction_2q` | holder crowding | `stk_holdernumber` | Falling holder count can proxy ownership concentration and reduced retail crowding. |
| `event_top_holder_concentration_change_1q` | holder concentration | `top10_holders`, `top10_floatholders` | Rising top-holder concentration can proxy informed accumulation, subject to industry/size neutralization. |

## Blocked Candidates

These candidates remain pre-registered as ideas, but they are blocked before IC work until coverage is repaired or a broader probe proves enough rows:

| Factor | Reason |
| --- | --- |
| `event_express_profit_surprise_1q` | `express` returned 0 rows in the smoke sample. |
| `event_share_unlock_pressure_60` | `share_float` returned 0 rows in the smoke sample. |
| `event_pledge_ratio_relief_1q` | `pledge_stat` returned 0 rows in the smoke sample. |

## Decision

Round146 passes as a direction-rotation and endpoint-availability gate, but it produces 0 promotable factors and 0 paper-ready factors.

The correct next step is not a portfolio grid. The next step is a PIT event coverage and IC prescreen for the 5 available candidates:

1. Normalize event rows to `asset_id`, `event_date`, `available_date`, and `next_trade_date`.
2. Enforce that `ann_date`, `ex_date`, `float_date`, or `end_date` is used only after it is tradable.
3. Join lagged market cap/price data only from dates known before the event signal date.
4. Require minimum cross-section per event date before IC is computed.
5. Run industry/size-neutral IC and quantile spread before any top-N portfolio test.
6. Count all 8 pre-registered candidates in multiple-testing records, even the 3 blocked ones.

## Engineering Outcome

Reusable artifacts added:

- `src/quant_robot/ops/event_factor_preregistration.py`
- `scripts/run_event_factor_preregistration.py`
- `tests/unit/test_event_factor_preregistration.py`
- `tests/unit/test_event_factor_preregistration_cli.py`
- `docs/superpowers/plans/2026-06-22-round146-event-factor-preregistration-plan.md`

Round146 improves the mining process because it rotates away from a failed final-holdout family into a genuinely different data source and forces event data availability before any return claim.
