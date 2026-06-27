# CN Stock Round455 Simulation Shortlist Blend Audit

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: audit whether the current 10 bps simulation-shortlist event streams can be combined into a better paper-simulation candidate.

## Reusable Tool Added

Round455 added a reusable blend audit:

- module: `src/quant_robot/ops/simulation_shortlist_blend_audit.py`
- CLI: `scripts/run_simulation_shortlist_blend_audit.py`
- tests: `tests/unit/test_simulation_shortlist_blend_audit.py`

The tool aligns event-return streams by date, enumerates discrete weights, calculates total return, annualized return, volatility, Sharpe, overlap-adjusted Sharpe, max drawdown, win rate, and component deltas, then blocks combinations with no aligned returns, severe alignment loss, non-positive return, drawdown beyond the configured floor, or high positive component correlation.

## Inputs

The comparable 10 bps event-return streams were:

- `default`: Round432 delayed-exit m150
- `range_q10`: Round442 range-contraction q10 m150
- `range_q20`: Round445 range-contraction q20 m175
- `entry_limit`: Round450 entry-limit-down cash rule

Command:

`python scripts\run_simulation_shortlist_blend_audit.py --return-source default=data/reports/round432_24h_profit_sprint_delayed_exit_m150_20260627/simulation_shortlist_entry_timed_events.csv --return-source range_q10=data/reports/round442_24h_profit_sprint_delayed_exit_incremental_range_contraction_overlay_20260627/simulation_shortlist_entry_timed_events.csv --return-source range_q20=data/reports/round445_24h_profit_sprint_range_contraction_incremental_sensitivity_20260627/round445_range_q20_m175/simulation_shortlist_entry_timed_events.csv --return-source entry_limit=data/reports/round450_24h_profit_sprint_entry_limit_down_formal_rebuild_20260627/simulation_shortlist_entry_timed_events.csv --output-dir data/reports/round455_24h_profit_sprint_simulation_blend_audit_20260627 --weight-step 0.25 --max-components 3 --max-drawdown-floor -0.30 --periods-per-year 50.4 --holding-period 20`

## Results

Summary:

- source count: 4
- tested cases: 34
- passed cases: 4
- blocked cases: 30
- best case: `range_q20_100`

Best passed single-source rows:

| case | annualized | total | overlap Sharpe | Sharpe | max drawdown | win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `range_q20_100` | 7.723% | +280.30% | 0.512 | 0.997 | -29.31% | 42.10% |
| `range_q10_100` | 7.083% | +241.70% | 0.505 | n/a | -26.99% | n/a |
| `entry_limit_100` | 6.829% | +227.43% | 0.515 | n/a | -24.88% | n/a |
| `default_100` | 6.663% | +218.46% | 0.496 | n/a | -26.21% | n/a |

All multi-component blends were blocked by high component return correlation. Pairwise correlations were:

| left | right | correlation |
| --- | --- | ---: |
| `default` | `range_q10` | 0.9988 |
| `range_q10` | `range_q20` | 0.9978 |
| `default` | `range_q20` | 0.9962 |
| `default` | `entry_limit` | 0.9959 |
| `entry_limit` | `range_q10` | 0.9952 |
| `entry_limit` | `range_q20` | 0.9928 |

The closest blends still underperformed the best component and were not diversified:

- `range_q10_25__range_q20_75`: annualized 7.563%, max drawdown -28.74%, blocked by high correlation.
- `entry_limit_25__range_q20_75`: annualized 7.500%, max drawdown -28.01%, blocked by high correlation.
- `default_25__range_q20_75`: annualized 7.458%, max drawdown about -28%, blocked by high correlation.

## Decision

No new blend candidate is promoted.

`range_q20_100` remains the highest-return aggressive observation under the user's roughly 30% drawdown tolerance, but it is not a new factor and it does not prove that weight blending adds value. The blend lane should stop unless a new component has materially lower return-stream correlation or a distinct economic source.

## Round455 Output

- new independent alpha factors: 0
- new simulation candidates from blending: 0
- reusable process/tool improvement: 1

The next action is the required Round453-455 three-round audit before any new mining batch.
