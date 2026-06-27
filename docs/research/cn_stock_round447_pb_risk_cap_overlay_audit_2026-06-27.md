# CN Stock Round447 PB Risk-Cap Overlay Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round447 tested whether the aggressive `range_contraction_lowvol_reversal_20` q20/m175 observation can be improved with an entry-known valuation risk cap:

- public factor: `range_contraction_lowvol_reversal_20`;
- selected side: top 20%;
- tilt multiplier: 1.75x;
- risk cap: if tilted trade has `pb > 4`, reduce only the incremental tilt;
- best cap multiplier: 0.50x;
- same cohort-entry-timed volatility target and self-risk overlay as the Round445 q20/m175 lane.

This is not a new standalone alpha family. It is a portfolio-construction/risk-budget repair around the existing range-contraction observation.

## Fair Control

The first audit pass found a comparability issue: older Round445 cost20/cost30 controls had a different cohort/event count from the newly rebuilt PB-cap variants. Round447 therefore reran current-entrypoint no-cap controls for cost20 and cost30 before judging incremental value.

Use only the fair-control outputs for this decision:

- `data/reports/round447_24h_profit_sprint_cost20_range_q20_m175_control_rerun_20260627`
- `data/reports/round447_24h_profit_sprint_cost30_vt070_range_q20_m175_control_rerun_20260627`

## Main Results

| Case | Annualized | Total | Overlap Sharpe | Max DD | Best-Month Share | OOS Ann. | OOS Strict |
|---|---:|---:|---:|---:|---:|---:|---:|
| q20 cost20 control | 7.233% | +234.73% | 0.484 | -31.76% | 49.02% | 11.184% | 90.00% |
| q20 cost20 PB cap050 | 7.301% | +238.45% | 0.498 | -30.26% | 47.49% | 11.461% | 90.00% |
| q20 cost30 VT7 control | 6.197% | +183.01% | 0.435 | -32.72% | 54.76% | 9.387% | 90.00% |
| q20 cost30 VT7 PB cap050 | 6.290% | +187.32% | 0.450 | -31.40% | 52.72% | 9.723% | 90.00% |

PB cap050 consistently improves overlap Sharpe, drawdown, and OOS mean return versus the fair no-cap control. The improvement is real but modest.

## Incremental CPCV/Bootstrap

Output:

`data/reports/round447_24h_profit_sprint_pb_risk_cap_incremental_cpcv_bootstrap_fair_20260627`

| Case | Delta Ann. | Delta Total | Delta Overlap | Delta DD | CPCV Ann Win | Bootstrap Ann Win | Bootstrap Overlap Win | Bootstrap DD Win |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cost20 PB cap050 | +0.068% | +3.71% | +0.014 | +1.49% | 67.50% | 68.80% | 98.00% | 97.40% |
| cost30 VT7 PB cap050 | +0.093% | +4.30% | +0.015 | +1.32% | 66.67% | 72.00% | 98.60% | 98.20% |
| cost10 PB cap075 | +0.029% | +1.76% | +0.010 | +0.92% | 65.83% | 58.40% | 97.80% | 97.20% |

The cap is most useful as a risk improvement. It is not a large return engine.

## Statistical Reality

Output:

`data/reports/round447_24h_profit_sprint_pb_risk_cap_stat_reality_fair_20260627`

Across 15 q20/m175 control and PB-cap hypotheses:

- Deflated Sharpe pass: 15;
- FDR-significant candidates: 0;
- statistical candidates: 0;
- best row by overlap Sharpe: `q20_cost10_pbcap050`;
- FDR q-value for the top rows is about 0.0704.

Interpretation: the improvement is coherent enough for simulation observation, but not strong enough to call final alpha.

## Decision

Keep `range_q20_m175_pb_gt4_cap050` as a risk-budget observation candidate, not as a default replacement and not as final promoted alpha.

Recommended use:

- 10 bps / 20 bps: compare PB cap050 against existing q20/m175 in paper simulation if aggressive return is prioritized;
- 30 bps: use only as stress evidence because best-month concentration stays above the strict 50% line and max drawdown remains worse than -30%;
- do not widen PB threshold or cap grids unless paper simulation specifically prioritizes drawdown repair around q20/m175.

## Process Lessons

- Always rerun fair controls with the same event generator before comparing variants.
- Use `simulation_shortlist_entry_timed_events.csv` for final candidate metrics; `cohort_source_period_returns.csv` is pre-overlay source evidence.
- Treat entry-known valuation fields such as `pb` as risk caps only after checking whether they remove right-tail winners.
- Rotate away from range/PB tuning after this round; the next mining work should test a genuinely different point-in-time family.
