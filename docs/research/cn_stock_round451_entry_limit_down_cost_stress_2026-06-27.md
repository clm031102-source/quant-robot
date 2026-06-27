# CN Stock Round451 Entry Limit Down Cost Stress

Date: 2026-06-27

Scope: test the Round450 `entry_limit_down` execution-risk rule under the
existing 20 bps and 30 bps delayed-exit cost-stress lanes. This is
research-to-review only. The 2026 final holdout remains sealed.

## Purpose

Round450 showed that cashing entry-limit-down trades improves the 10 bps
delayed-exit lane on full-sample and beta-adjusted diagnostics, but not on mean
OOS. Round451 asks whether the same rule is more useful under heavier
transaction-cost assumptions.

This is not a new alpha search. It is a cost-stress validation of an execution
risk rule.

## Inputs

Cost 20 bps base:

- `data/reports/round433_24h_profit_sprint_delayed_exit_cost20_m150_20260627/cohort_trade_rows.csv`
- base events:
  `data/reports/round433_24h_profit_sprint_delayed_exit_cost20_m150_20260627/simulation_shortlist_entry_timed_events.csv`

Cost 30 bps base:

- `data/reports/round433_24h_profit_sprint_delayed_exit_cost30_vt075_max100_m150_20260627/cohort_trade_rows.csv`
- base events:
  `data/reports/round433_24h_profit_sprint_delayed_exit_cost30_vt075_max100_m150_20260627/simulation_shortlist_entry_timed_events.csv`

Rule:

`entry_limit_down=entry_blocked_reasons:eq:limit_down_like;limit_down_official`

Outputs:

- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost20_formal_rebuild_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost30_vt075_formal_rebuild_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost20_oos_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost30_vt075_oos_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost20_block_audit_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost30_vt075_block_audit_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost20_incremental_robustness_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost30_vt075_incremental_robustness_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost20_beta_20260627`
- `data/reports/round451_24h_profit_sprint_entry_limit_down_cost30_vt075_beta_20260627`

## Full-Sample Cost Stress

| Cost lane | Candidate | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Best 3M Log Share |
|---|---|---:|---:|---:|---:|---:|---:|
| 20 bps | base | 6.060% | +187.60% | 0.888 | 0.456 | -28.07% | 49.87% |
| 20 bps | entry-limit-down | 6.228% | +195.90% | 0.915 | 0.475 | -25.83% | 48.56% |
| 30 bps VT7.5 | base | 5.415% | +157.79% | 0.809 | 0.416 | -29.66% | 55.28% |
| 30 bps VT7.5 | entry-limit-down | 5.590% | +165.55% | 0.838 | 0.435 | -27.40% | 53.60% |

Full sample favors entry-limit-down under both cost assumptions.

## OOS Split Audit

OOS does not favor entry-limit-down:

| Cost lane | Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---|---:|---:|---:|---:|
| 20 bps | base | 9.132% | 0.759 | -19.75% | 76.67% |
| 20 bps | entry-limit-down | 9.108% | 0.757 | -19.83% | 76.67% |
| 30 bps VT7.5 | base | 8.197% | 0.684 | -20.28% | 76.67% |
| 30 bps VT7.5 | entry-limit-down | 8.177% | 0.684 | -20.28% | 76.67% |

The differences are small, but the base remains the OOS winner in both lanes.

## Incremental Robustness

| Cost lane | CPCV Ann Win | CPCV Overlap Win | CPCV DD Win | Bootstrap Ann Win | Bootstrap Overlap Win | Bootstrap DD Win | Year Win |
|---|---:|---:|---:|---:|---:|---:|---:|
| 20 bps | 70.00% | 70.00% | 65.00% | 78.70% | 88.40% | 89.10% | 36.36% |
| 30 bps VT7.5 | 76.67% | 75.83% | 75.00% | 80.40% | 89.00% | 88.80% | 63.64% |

The heavier 30 bps lane is more supportive than 20 bps on year win and CPCV,
but bootstrap strict-pass remains below 50% in both lanes.

## Beta Diagnostics

| Cost lane | Candidate | Hedged Ann. | Hedged Overlap | Hedged DD | Alpha t |
|---|---|---:|---:|---:|---:|
| 20 bps | base | 6.744% | 0.724 | -14.14% | 3.97 |
| 20 bps | entry-limit-down | 6.836% | 0.732 | -13.86% | 4.02 |
| 30 bps VT7.5 | base | 5.952% | 0.651 | -14.36% | 3.57 |
| 30 bps VT7.5 | entry-limit-down | 6.057% | 0.659 | -14.07% | 3.63 |

Beta diagnostics support the rule as a small execution/risk repair.

## Decision

Round451 promotes 0 new independent alpha factors.

Entry-limit-down remains a paper-simulation comparison observation, not a
default replacement:

- It improves full-sample total return, Sharpe, overlap Sharpe, max drawdown,
  and beta-hedged diagnostics under 20 bps and 30 bps.
- It does not beat the base on mean OOS annualized return or mean OOS overlap.
- The 20 bps year win rate is weak at 36.36%.
- The rule is an execution-risk repair, not a standalone return engine.

Keep it available as an execution-risk comparison lane for simulation review.
Do not continue tuning entry-limit-down or adjacent tradeability strings.

Next direction: rotate back to a genuinely independent point-in-time source or
run a three-round audit after one more distinct validation/mining action.

Safety: research-to-review only. No broker connection, no account reads, no
orders, and no live trading.
