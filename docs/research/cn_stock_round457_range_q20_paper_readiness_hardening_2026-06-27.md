# CN Stock Round457 Range Q20 Paper Readiness Hardening

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: harden the Round456 primary high-return paper candidate before the project enters paper-simulation review.

Primary candidate:

`paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`

## Executive Decision

Round457 promotes 0 new independent alpha factors.

It keeps `range_q20_m175` as the primary high-return paper-simulation lane, not as the conservative default and not as a final promoted alpha.

The candidate is worth paper simulation because the 10 bps profile is strong and within the user's roughly 30% drawdown tolerance:

- annualized return: 7.723%
- total return: +280.30%
- overlap-adjusted Sharpe: 0.512
- max drawdown: -29.31%
- mean OOS annualized return: 11.739%
- OOS strict pass rate: 90%

The candidate must carry explicit red flags:

- heavier-cost drawdown crosses the 30% soft line;
- 123 extreme gross-return trades contribute about 35.2% of total contribution;
- return streams remain highly correlated with the default/range family, so this is a simulation lane, not a new independent alpha.

## Replay And Schema

Current simulation shortlist replay passed:

- output: `data/reports/round457_24h_profit_sprint_current_shortlist_replay_20260627`
- configured candidates: 17
- replayed candidates: 17
- blockers: 0

The high-return candidate event file contains the paper-needed event fields:

- `date`
- `decision_date`
- `raw_period_return`
- `vol_target_exposure`
- `source_period_return`
- `prior_roll21_sum`
- `self_risk_exposure`
- `final_exposure`
- `period_return`
- `equity`
- `drawdown`

Cohort facts:

- candidate universe trade count: 26,450
- factor matched trade count: 26,400
- missing factor trade count: 50
- missing factor share: 0.189%
- public tilt trade count: 5,808
- cohort count: 1,113
- unique exit dates: 905
- duplicate exit-date row count: 208
- average final exposure: 0.876
- self-risk guard event share: 36.39%

## Capacity Stress

Command:

`python scripts\run_trade_capacity_stress.py --trade-source range_q20_m175=data\reports\round445_24h_profit_sprint_range_contraction_incremental_sensitivity_20260627\round445_range_q20_m175\cohort_trade_rows.csv --output-dir data\reports\round457_24h_profit_sprint_range_q20_capacity_stress_20260627 --multipliers 1,5,10,20,50,100 --max-participation-rate 0.05`

The trade capacity tool was extended to read CSV as well as Parquet trade sources.

Capacity result:

| AUM multiplier | p95 participation | p99 participation | max participation | breach trades | breach rate | safe |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1x | 0.0405% | 0.0598% | 0.1280% | 0 | 0.000% | yes |
| 5x | 0.2025% | 0.2991% | 0.6400% | 0 | 0.000% | yes |
| 10x | 0.4049% | 0.5983% | 1.2801% | 0 | 0.000% | yes |
| 20x | 0.8098% | 1.1965% | 2.5601% | 0 | 0.000% | yes |
| 50x | 2.0246% | 2.9913% | 6.4003% | 6 | 0.029% | no |
| 100x | 4.0492% | 5.9826% | 12.8007% | 477 | 2.340% | no |

Interpretation: capacity is clean through 20x under a 5% ADV participation cap. It is not clean at 50x and above.

## Cost Stress

The 10 bps high-return lane is inside the user's 30% drawdown tolerance:

- annualized return: 7.723%
- max drawdown: -29.31%

Existing cost-stress outputs show the limitation:

| Case | Annualized | Total | Overlap Sharpe | Max DD |
| --- | ---: | ---: | ---: | ---: |
| 20 bps, VT 8% | 7.061% | +240.44% | 0.475 | -31.07% |
| 20 bps, VT 7.5% | 6.901% | +231.46% | 0.473 | -30.63% |
| 30 bps, VT 7% | 6.057% | +187.46% | 0.428 | -32.04% |
| Round447 20 bps control rerun | 7.233% | +234.73% | 0.484 | -31.76% |
| Round447 30 bps VT7 control rerun | 6.197% | +183.01% | 0.435 | -32.72% |

Interpretation: the candidate is a 10 bps high-return paper lane. It is not a cost-stress default.

## Extreme Trade Profile

Command:

`python scripts\run_shortlist_extreme_trade_profile.py --trades data\reports\round445_24h_profit_sprint_range_contraction_incremental_sensitivity_20260627\round445_range_q20_m175\cohort_trade_rows.csv --output-dir data\reports\round457_24h_profit_sprint_range_q20_extreme_trade_profile_20260627 --group-column industry --group-column stock_market --group-column entry_blocked_reasons --group-column delayed_exit_status --numeric-column participation_rate --numeric-column turnover_rate_f --numeric-column pb --numeric-column ps_ttm --numeric-column circ_mv --threshold 0.50 --gross-return-column delayed_exit_gross_return --contribution-column final_return_contribution --active-weight-column final_target_weight --top-n 50 --min-group-extreme-count 5 --min-extreme-rate-lift 2.0`

Summary:

- source trade count: 26,450
- active trade count: 26,090
- extreme gross-return trades over 50%: 123
- extreme trade rate: 0.471%
- positive extreme trades: 119
- negative extreme trades: 4
- max absolute gross return: 254.02%
- total contribution sum: 1.3905
- extreme contribution sum: 0.4896
- extreme contribution share: about 35.2%

Risk clusters:

- delayed-exit trades: 13 extreme trades, 6.53% extreme rate, 13.86x lift
- supermarket retail: 5 extreme trades, 3.31% extreme rate, 7.02x lift
- glass: 6 extreme trades, 2.48% extreme rate, 5.26x lift
- semiconductor: 5 extreme trades, 2.26% extreme rate, 4.80x lift
- biopharma: 5 extreme trades, 1.96% extreme rate, 4.16x lift
- electrical equipment: 7 extreme trades, 1.04% extreme rate, 2.20x lift

Numeric contrast between extreme and non-extreme trades:

- turnover_rate_f: 3.626 versus 2.023
- PB: 5.973 versus 3.323
- PS: 4.099 versus 5.124
- circ_mv: 3.901m versus 3.248m in config units
- participation rate was not higher for extreme trades

Interpretation: the return is not obviously a capacity artifact, but it does rely meaningfully on rare positive tail trades. Paper simulation should monitor these clusters rather than suppress them with a post-outcome rule.

## Round457 Output

- new independent alpha factors: 0
- paper-simulation high-return lane retained: 1
- process/tool improvement: CSV support for `trade_capacity_stress`
- primary blocker against final promotion: cost stress plus extreme-trade concentration

## Next Direction

Round458 should either:

- build a paper-simulation operations package that includes the conservative default and this high-return lane; or
- search for a genuinely independent cached PIT source that can diversify away from the current correlated range/Alpha101/Dragon-Hot family.

Do not widen `range_contraction_lowvol_reversal_20` parameters further. The current high-return lane is already selected for paper comparison.
