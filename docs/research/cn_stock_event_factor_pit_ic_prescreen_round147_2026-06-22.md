# CN Stock Event Factor PIT/IC Prescreen Round147

- Date: 2026-06-22
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock event-factor mining, research-to-review only
- Source audit: `docs/research/cn_stock_event_factor_preregistration_round146_2026-06-22.md`
- Output pack: `data/reports/event_factor_pit_ic_prescreen_round147_20260622`

## Objective

Round147 tested the 5 Round146 available event candidates as point-in-time signals before any portfolio grid:

1. Convert Tushare event rows from `ts_code` to project `asset_id`.
2. Use event `ann_date` as the known-information date.
3. Shift each event to the next tradable signal date before joining labels.
4. Evaluate 5-day and 20-day forward returns.
5. Require FDR, quantile spread, industry-neutral IC, and size-neutral IC before a research lead is allowed.

No 2026 final-holdout data was used for this prescreen.

## Live Run

Command:

```powershell
python scripts\run_event_factor_pit_ic_prescreen.py --event-start-year 2018 --event-end-year 2025 --max-periods 32 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 30 --min-ic-observations 8 --output-dir data\reports\event_factor_pit_ic_prescreen_round147_20260622
```

The output pack was written and audited locally. The live Tushare event pull is slow enough that future runs should shard/cache event endpoint downloads instead of doing a single monolithic live request.

## Summary

| Metric | Value |
| --- | ---: |
| Candidate factors | 5 |
| Factor rows | 216,112 |
| Label rows | 21,417,227 |
| Aligned rows | 423,204 |
| Tests | 10 |
| FDR-significant tests | 6 |
| Neutral-gate pass tests | 2 |
| Research leads | 1 |
| Promotion allowed | 0 |

Event rows by endpoint:

| Endpoint | Rows |
| --- | ---: |
| `dividend` | 15,996 |
| `forecast` | 6,916 |
| `repurchase` | 9,575 |
| `stk_holdernumber` | 164,422 |
| `top10_holders` | 192,000 |
| `top10_floatholders` | 180,000 |

## Results

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Industry-neutral IC | Size-neutral IC | Lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `event_dividend_cash_yield_announced_1y` | 20 | 0.1082 | 0.629 | 6.62 | 75.7% | 0.0223 | 0.2780 | 0.1003 | yes |
| `event_repurchase_amount_to_mv_20` | 20 | 0.0788 | 0.440 | 4.08 | 65.1% | 0.0260 | 0.2388 | 0.0355 | no |
| `event_dividend_cash_yield_announced_1y` | 5 | 0.0633 | 0.297 | 3.13 | 61.3% | 0.0065 | 0.2522 | 0.0560 | no |
| `event_repurchase_amount_to_mv_20` | 5 | 0.0454 | 0.239 | 2.22 | 60.5% | 0.0044 | 0.2394 | 0.0072 | no |
| `event_holder_number_contraction_2q` | 20 | 0.0395 | 0.279 | 9.87 | 62.7% | 0.0087 | 0.3020 | 0.0139 | no |
| `event_holder_number_contraction_2q` | 5 | 0.0364 | 0.256 | 9.11 | 60.6% | 0.0051 | 0.3040 | 0.0136 | no |
| `event_top_holder_concentration_change_1q` | 20 | 0.0110 | 0.096 | 1.53 | 56.0% | 0.0014 | 0.3283 | 0.0056 | no |
| `event_top_holder_concentration_change_1q` | 5 | 0.0102 | 0.092 | 1.46 | 53.2% | -0.0005 | 0.3366 | 0.0101 | no |
| `event_forecast_profit_revision_1q` | 20 | -0.0415 | -0.221 | -0.73 | 36.4% | -0.0082 | 0.3253 | -0.0468 | no |
| `event_forecast_profit_revision_1q` | 5 | 0.0033 | 0.022 | 0.07 | 54.5% | 0.0045 | 0.2604 | -0.0065 | no |

## Interpretation

`event_dividend_cash_yield_announced_1y` at 20 days is the first useful event-family research lead from this line. It passed:

- FDR after 10 event factor x horizon tests
- 111 IC observations
- IC 0.1082, ICIR 0.629, t-stat 6.62
- Industry-neutral IC 0.2780, t-stat 12.10
- Size-neutral IC 0.1003, t-stat 5.93
- Positive quantile spread

This is still not paper-ready. The signal may still be affected by dividend endpoint revision semantics, event clustering around annual reports, ex-right pricing, high event-cohort turnover, and hidden value/quality exposure. It must next pass de-duplication, PIT dividend-field audit, cost/capacity-aware portfolio conversion, regime coverage, walk-forward, and final-holdout readiness/result gates.

## Rejections

- `event_repurchase_amount_to_mv_20` has promising raw and industry-neutral IC, but size-neutral retention is weak, so it is not a lead.
- `event_holder_number_contraction_2q` has strong statistical t-stats but fails ICIR/monotonicity/size-neutral quality, so it is not promoted.
- `event_top_holder_concentration_change_1q` has industry-neutral signal but weak overall IC and weak size-neutral evidence.
- `event_forecast_profit_revision_1q` is not usable in this implementation: overall IC is weak or negative, and forecast sampling by selected `ann_date` remains low-power.

## Decision

Round147 produces:

- 1 research lead: `event_dividend_cash_yield_announced_1y`, horizon 20
- 0 paper-ready factors
- 0 promotable factors
- 0 live-usable signals

The correct next direction is:

`round148_event_factor_neutral_lead_dedup_before_portfolio_conversion`

Round148 must not expand parameters. It should only audit and de-duplicate the single dividend event lead, then decide whether a constrained portfolio conversion is justified.

## Engineering Outcome

Reusable artifacts added:

- `src/quant_robot/ops/event_factor_pit_ic_prescreen.py`
- `scripts/run_event_factor_pit_ic_prescreen.py`
- `tests/unit/test_event_factor_pit_ic_prescreen.py`
- `tests/unit/test_event_factor_pit_ic_prescreen_cli.py`

The process is now less blind: event hypotheses are required to pass PIT and neutral IC gates before any portfolio grid can consume capital and time.
