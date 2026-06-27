# CN Stock Round425 Simulation Paper Handoff

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access.

## Purpose

Round425 turns the current best cohort-entry-timed candidates into a repeatable paper-simulation handoff pack. The handoff is intentionally stricter than the earlier event-level shortlist: a candidate must be reconstructable at entry decision time and must preserve entry/exit cohort timing.

Output:

`data/reports/round425_24h_profit_sprint_simulation_paper_handoff_20260627`

Command:

```powershell
python scripts\run_simulation_shortlist_paper_handoff.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round425_24h_profit_sprint_simulation_paper_handoff_20260627
```

## Gate Result

| Candidate | Role | Cost | Annualized | Sharpe | Overlap Sharpe | Max DD | Win Rate | OOS Strict Pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08` | default | 10 bps | 5.76% | 0.863 | 0.466 | -29.18% | 40.71% | 90.00% |
| `cost20_cohort_openclose_vt07_max1p0_sr21_x0p8` | heavy-cost lane | 20 bps | 5.05% | 0.788 | 0.423 | -29.96% | 40.37% | 90.00% |
| `cost30_cohort_openclose_vt07_max0p85_sr21_x0p8` | stress fallback | 30 bps | 4.23% | 0.727 | 0.387 | -28.89% | 40.02% | 76.67% |

Summary:

- candidate count: 3
- ready for paper simulation: 3
- blocked: 0
- default candidate: `paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08`

## Decision

Use the 10 bps cohort candidate as the default simulated paper lane. Use the 20 bps variant when the simulation needs heavier cost conservatism. Keep the 30 bps variant as a stress fallback only: it stays within the -30% drawdown tolerance, but its return and overlap Sharpe are lower and its OOS strict-pass rate is only 76.67%.

Do not use the older aggregate entry-timed candidates as paper-simulation handoffs. They can remain research observations, but the handoff rule is now cohort-entry-timed only.

## Reusable Process Added

New reusable files:

- `src/quant_robot/ops/simulation_shortlist_paper_handoff.py`
- `scripts/run_simulation_shortlist_paper_handoff.py`
- `tests/unit/test_simulation_shortlist_paper_handoff.py`
- `tests/unit/test_simulation_shortlist_paper_handoff_cli.py`

The handoff gate requires:

- `evidence.paper_ready = true`
- cohort + entry-timed status or id
- readable event-return source
- positive recomputed annualized return
- max drawdown no worse than -30%
- OOS strict-pass rate at least 75%

## Next Direction

With a paper-simulation-safe handoff now frozen, the next mining work should avoid further small tweaks to the same Dragon-Hot/Alpha101 lane unless they materially improve the cohort-ready handoff. The highest-value next search is an independent, lower-correlation family that can pass the same cohort-entry-timed gate.
