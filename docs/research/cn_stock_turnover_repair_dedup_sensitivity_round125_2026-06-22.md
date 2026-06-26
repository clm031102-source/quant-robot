# CN Stock Turnover Repair Dedup Sensitivity Round125 - 2026-06-22

## Scope

Round125 audited the five Round124 turnover-repair research-lead rows before allowing any portfolio conversion.

Input:

`data/reports/turnover_continuous_capacity_repair_prescreen_round124_20260622/turnover_continuous_capacity_repair_prescreen_results.csv`

Output:

`data/reports/turnover_repair_dedup_sensitivity_round125_20260622`

This is still research-to-review only. It does not use the 2026 final holdout and it does not authorize paper, manual, or live trading.

## Result

| Metric | Value |
|---|---:|
| Round124 input tests | 12 |
| Research-lead rows audited | 5 |
| Unique research-lead factor names | 3 |
| Raw-source clusters | 2 |
| Raw-clone lead rows | 4 |
| High-redundancy lead rows | 1 |
| Nonredundant research leads | 0 |
| Capacity-clean rows across 100k, 500k, 1m, 5m | 5 |
| Portfolio conversion candidates allowed | 1 |
| Promotion allowed | 0 |

## Champion For Next Audit

Only one frozen candidate is allowed to enter a costed portfolio-conversion audit:

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Mono | Top turnover | Raw corr | Max participation at 100k | Max participation at 5m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_f_low_participation_budget_100k_20` | 20 | 0.1033 | 0.6485 | 33.35 | 75.35% | 0.0673 | 0.900 | 27.81% | 1.000 | 0.0100% | 0.5000% |

Interpretation:

- The signal is strong as a long-cycle IC/quantile lead.
- The continuous participation-budget repair keeps capacity clean under the small-capital sensitivity grid.
- It is not an independent new alpha. It is an execution repair of the raw `turnover_rate_f_low` engine.
- It can only advance to one narrow costed TopN conversion audit with frozen parameters.

## Dedup Table

| Factor | Horizon | IC | ICIR | t-stat | Raw corr | Dedup class | Capacity all clean | Action |
|---|---:|---:|---:|---:|---:|---|---|---|
| `turnover_rate_f_low_participation_budget_100k_20` | 20 | 0.1033 | 0.6485 | 33.35 | 1.0000 | exact raw clone | yes | single frozen champion costed conversion |
| `turnover_rate_low_participation_budget_100k_20` | 20 | 0.0973 | 0.5563 | 28.61 | 1.0000 | exact raw clone | yes | blocked as independent alpha |
| `turnover_rate_f_low_participation_budget_100k_20` | 5 | 0.0775 | 0.4917 | 25.36 | 1.0000 | exact raw clone | yes | blocked as independent alpha |
| `turnover_rate_low_participation_budget_100k_20` | 5 | 0.0718 | 0.4257 | 21.95 | 1.0000 | exact raw clone | yes | blocked as independent alpha |
| `turnover_rate_f_low_adv_soft_rank_20` | 5 | 0.0522 | 0.3030 | 15.63 | 0.7899 | high-redundancy soft variant | yes | secondary diagnostic only |

## Why Promotion Is Still Blocked

Promotion blockers:

- `dedup_revealed_zero_independent_new_alpha`
- `costed_topn_portfolio_missing`
- `rolling_walk_forward_cost_regime_overlap_gates_missing`
- `final_holdout_not_read_for_promotion`

This means the repaired low-turnover line is not dead, but the project must not count the five Round124 rows as five new factors. The evidence says one raw low-turnover return engine may have a cleaner small-capital implementation.

## Decision

Next direction:

`round126_turnover_repair_champion_costed_portfolio_conversion`

Allowed:

- one frozen champion;
- costed TopN conversion only;
- capacity, extreme-return, turnover, overlap-aware return, and regime diagnostics;
- no 2026 final holdout read.

Rejected:

- direct promotion from Round125;
- broad turnover-repair parameter grid;
- treating duplicate lead rows as independent alpha;
- manual/live use.

