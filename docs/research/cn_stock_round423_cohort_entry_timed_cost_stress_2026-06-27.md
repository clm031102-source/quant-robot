# CN Stock Round423 - Cohort Entry-Timed Cost Stress

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round423 tests the cohort-level paper-ready candidate under 5/10/20/30 bps equivalent transaction-cost assumptions.

The test rebuilds trade-level returns from `gross_return`, `target_weight`, and the selected cost rate, then regenerates cohort-level entry-timed events.

Candidate:

`paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08`

## Cost Stress Result

| Cost | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD | LOY Min Ann. | Best Month Share |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 bps | +176.60% | 6.06% | 0.904 | 0.487 | -28.36% | 4.16% | 45.80% |
| 10 bps | +163.48% | 5.76% | 0.863 | 0.466 | -29.18% | 3.84% | 48.00% |
| 20 bps | +140.93% | 5.21% | 0.789 | 0.426 | -30.94% | 3.26% | 52.66% |
| 30 bps | +118.34% | 4.62% | 0.705 | 0.382 | -32.94% | 2.62% | 59.05% |

## Interpretation

The candidate is not cost-fragile, because all tested cost levels retain positive full-sample total and annualized returns.

But it is drawdown-sensitive:

- 5 and 10 bps stay within the user's -30% drawdown tolerance;
- 20 and 30 bps breach the -30% tolerance;
- 30 bps also pushes best-month contribution close to the 60% concentration gate.

## Decision

Use the 10 bps cohort-level candidate as the current paper-simulation handoff.

If the simulator uses 20-30 bps equivalent slippage/cost, the next step is a lower-risk cohort cost-stress grid, not immediate promotion.
