# CN Stock Round364 Public Indicator Filter On Primary Replacement Quickcheck

Date: 2026-06-27

Machine/task: `office_desktop` / `factor_validation`

Safety boundary: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Purpose

Round265 showed that public technical indicators failed as standalone residual alpha. Round336 showed that direct public-indicator cash filters did not beat the simpler low-turnover repair baseline.

Round364 retests public indicators in a narrower role: a second-stage risk filter inside the current primary replacement candidate:

`replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84 + ZZ500 risk-off overlay`

The goal is not to create a new public-indicator TopN factor. It is to check whether public indicators can remove weak selected trades from the existing low-turnover replacement basket.

## Inputs

- Replacement trade file: `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`
- Official event-calendar template: `data/reports/round339_24h_profit_sprint_replacement_filters_voltarget_wrappers_20260627/replace_drop_turnover_f_low10_base_period_returns.csv`
- Public indicator values: `data/reports/round336_24h_profit_sprint_turnover_low_public_indicator_cash_filters_20260627/public_indicator_values_for_turnover_low_assets.parquet`
- ZZ500 regime exposures: Round351 `primary_low10_vol6_zz500_mult_*_cost10_events.csv`

The corrected run uses the official 834-date event template. A first local attempt grouped by `exit_date + entry_date`, produced 1,071 events, and was rejected as an invalid calendar mismatch.

## Screen

Tested 44 filters:

- 22 public indicators;
- top 20% cash filter;
- bottom 20% cash filter.

For each filter:

1. Rank the public indicator within the selected `replace_drop_turnover_f_low10` basket on each `signal_date`.
2. Cash the selected top or bottom 20% entry-allowed trades.
3. Preserve entry-blocked cash behavior.
4. Aggregate to the official event calendar.
5. Apply `vol_target_6_lb84`.
6. Apply ZZ500 risk-off multipliers 100%, 75%, and 50%.

Output:

`data/reports/round364_24h_profit_sprint_public_indicator_on_primary_replacement_quickcheck_20260627`

## Baseline Reproduction

The corrected baseline reproduces Round351:

| Variant | Annualized | Sharpe | Overlap Sharpe | Max DD | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| no ZZ500, vol6 | 6.35% | 0.960 | 0.517 | -28.88% | +177.08% |
| ZZ500 75% | 5.99% | 0.989 | 0.530 | -24.74% | +161.99% |
| ZZ500 50% | 5.62% | 1.001 | 0.536 | -20.38% | +147.29% |

## Best Result

Best defensive filter:

`public_adx_trend_strength_exhaustion_reversal_14_20_cash_bottom20_on_primary_low10`

| Variant | Annualized | Sharpe | Overlap Sharpe | Max DD | Delta Ann. vs Base | Delta Overlap vs Base | Delta DD vs Base |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ZZ500 100% | 6.18% | 1.029 | 0.558 | -24.26% | -0.17% | +0.041 | +4.62% |
| ZZ500 75% | 5.76% | 1.050 | 0.566 | -20.64% | -0.23% | +0.036 | +4.10% |
| ZZ500 50% | 5.34% | 1.050 | 0.565 | -16.87% | -0.29% | +0.029 | +3.51% |

Block-dependence audit:

- all three ADX variants passed the loose leave-one-year and top-month concentration checks;
- worst removed year remains 2015;
- top-three-month log share is about 42% to 43%;
- 50% ZZ500 ADX variant leave-one-year minimum annualized return is 3.20%;
- 50% ZZ500 ADX variant leave-one-year minimum overlap Sharpe is 0.501.

## Interpretation

This is the first public-indicator result in this sprint that is not just a failed standalone alpha. The signal is useful as a defensive filter:

- it reduces drawdown materially versus `primary_defensive_zz500`;
- it improves overlap Sharpe;
- it keeps annualized return above the existing PS-filtered defensive observation lane;
- it does not beat the primary 50% or 75% lanes on return.

It should not replace the main shortlist yet. Current status:

- research lead: yes;
- simulation shortlist: not yet;
- promotion: no;
- final holdout: untouched.

## Next Checks

Before adding this to the simulation shortlist:

1. Run cross-split OOS checks in the same style as Round350/354.
2. Run event-schema replay after packaging the event source.
3. Run beta/cost quickcheck against CSI500 and HS300.
4. Compare directly with `primary_ps_filtered_defensive_zz500` and `primary_defensive_zz500` on block dependence and 30 bps cost stress.
