# CN Stock Round262 Data Source Availability And Direction Audit - 2026-06-26

## Scope

Round262 is an audit and process-optimization round, not a new alpha discovery batch.

- Machine/task: `office_desktop` / `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market/scope: CN A-share stock cross-sectional alpha research
- Not scope: CN ETF rotation, broker connection, account reads, orders, live trading
- Final holdout: not used

The purpose was to prevent another blind family expansion after Rounds 259-261 produced zero residual leads. The new rule is: choose a factor family only after the required data source is accessible, point-in-time safe, and long-cycle usable.

## Inputs Reviewed

Local processed data:

- long-cycle CN stock bars and daily-basic inputs;
- official tradeability mask/cache from the Round198-Round199 path;
- dragon-tiger processed event data;
- forecast/express cache;
- limited financial-statement and `fina_indicator` shards;
- historical reports for the low-turnover repair path, especially Round125 and Round126.

Tushare endpoint probes:

| Endpoint or family | Result | Decision |
|---|---|---|
| `cyq_perf`, `cyq_chips`, `stk_factor` | permission blocked, code `40203` | do not generate factors from these endpoints |
| `ths_index`, `ths_member`, `sw_daily` | permission blocked, code `40203` | do not generate THS/SW-daily factors from these endpoints |
| `concept`, `concept_detail` | not usable in this probe, code `40101` | do not depend on this namespace |
| `index_classify`, `index_member`, `index_member_all` | accessible | use as industry classification/control infrastructure |
| `index_weekly` | accessible for SW index weekly data | control or regime descriptor only, not a direct alpha family after Round261 failure |

`index_member_all` sample:

- rows: 5,864
- unique `ts_code`: 5,864
- level-1 industries: 31
- level-2 industries: 131
- level-3 industries: 337
- `in_date`: non-null for all rows, min 1989-11-01, max 2026-06-05
- `out_date`: empty in the current probe

## Main Findings

1. Chip and smart-money style endpoint access is not available under the current token.

This blocks any honest use of chip distribution or Tushare `stk_factor` as the next direct alpha source. The project must not burn cycles designing formulas on endpoints that cannot be fetched.

2. SW industry membership is useful, but only as a control layer.

The accessible SW membership data can improve industry neutralization, grouping, and control reports. It should not be treated as a standalone event alpha because `out_date` is empty in the probe and Round261 already showed that industry-state transformations can have raw/neutral IC that collapses after residualization.

3. Financial statement coverage remains too thin for broad direct mining.

The available full-universe financial coverage is still a data-engineering path rather than a broad alpha source. Direct profitability factor generation should remain blocked until PIT coverage and cross-section coverage are adequate.

4. Round126 failed for real portfolio reasons, not because the raw signal had no return.

The Round125 champion `turnover_rate_f_low_participation_budget_100k_20` had strong long-cycle IC evidence, but Round126 costed TopN conversion rejected all 12 cost/capital cases:

- best total return: 1094.25%
- best annualized return: 11.90%
- best overlap-adjusted Sharpe: 0.226
- best Newey-West t-stat on mean return: 1.061
- max drawdown range: -69.55% to -79.82%
- extreme trade return rate: 1.61%
- max absolute gross trade return: 205.39
- capacity-limited trades: 0 at 100k, 500k, 1m; 12 at 5m

The user's 30% drawdown tolerance does not rescue this line. The best drawdown was already beyond -69%, and the extreme-trade diagnostics point to data quality, microstructure, relisting, suspension, or adjustment artifacts. Capacity and extreme-trade gates remain hard gates.

5. The 2015 redundancy risk is a common hidden engine.

Several historical bright spots benefited from 2015-style A-share microstructure: crash/rebound, liquidity segmentation, small-cap crowding, suspension/reopening, and low-turnover selection. A factor that looks independent but earns mostly from the same 2015 regime can be redundant with the low-vol/reversal/liquidity/low-turnover cluster. Future recovery audits must show year and regime contribution, not just full-sample totals.

## Direction Decision

Round262 completes the data-source availability audit and selects the next work mode:

`round263_rotate_to_tradeable_historical_lead_recovery_audit`

This is not permission to restart low-turnover parameter tuning. It is a frozen-parameter recovery audit over the best historical leads to answer one narrow question:

Can any previously bright signal survive the improved gates when using the same old parameters, official tradeability masks, long-cycle replay, overlap-aware statistics, cost/capacity stress, extreme-trade diagnostics, industry/style residual checks, and regime/year contribution?

## Round263 Candidate Pool

Round263 should start from a small frozen pool, not a new grid:

| Historical lead | Source | Why include | Hard caution |
|---|---|---|---|
| `turnover_rate_f_low_participation_budget_100k_20` | Round125/126 | strongest low-turnover repaired IC lead | Round126 portfolio path failed; audit only |
| `alpha101_rank_pv_reversal_liquid_20` | Round128-130 | public Alpha101-style price-volume reversal lead | previously redundant and residual-negative |
| `qlib_alpha158_return_std_position_blend_20` | Round115/116 | public/Qlib-style IC lead with all-year positive diagnostic | low-vol/reversal/liquidity redundancy |
| `beta_adjusted_range_contraction_60` | Round111/112 | clean IC/quantile shape | 2015 and exposure redundancy risk |
| clean daily-basic carry/free-float survivors, if any | Rounds 132-140 | possible non-price data path | extreme-trade and price-basis repairs required |

Any candidate that fails the recovery audit remains hibernated. Passing the recovery audit only permits walk-forward validation, not promotion.

## New Repeatable Rule

Before every new mining family:

1. Confirm data source availability and permissions.
2. Confirm PIT or lag-safe availability date semantics.
3. Confirm long-cycle coverage is adequate.
4. Confirm the family is not a hibernated family reentered by parameter tweaking.
5. Confirm short-window smoke results cannot be counted as profitability evidence.
6. Confirm promotion still requires cost, capacity, overlap-aware statistics, regime coverage, and no final-holdout tuning.

## Outputs

- New report: `docs/research/cn_stock_round262_data_source_availability_and_direction_audit_2026-06-26.md`
- Startup gate updated to Round263 direction.
- Data-source availability protocol added to the repeatable startup gate.
- No new factor, portfolio candidate, paper-ready signal, manual signal, or live signal was produced in Round262.

