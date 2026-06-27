# CN Stock Round433 Delayed-Exit Cost Stress And Handoff Gate

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round432 promoted `round432_delayed_exit_m150` to the best research-to-paper candidate, but it still needed transaction-cost stress before replacing the Round425 conditional handoff pack.

Round433 tests the same delayed-exit execution logic under 20 bps and 30 bps round-trip cost assumptions, then checks OOS, block dependence, and beta-adjusted residual performance.

## Reusable Code Added

`src/quant_robot/ops/shortlist_delayed_exit_return_repair.py` and `scripts/run_shortlist_delayed_exit_return_repair.py` now support:

- `override_cost_rate`
- `--override-cost-rate`

This lets future runs recompute delayed-exit weighted returns under 10/20/30 bps without hand-editing trade files.

## Full-Sample Cost Stress

| Candidate | Cost | Risk Budget | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Blockers |
|---|---:|---|---:|---:|---:|---:|---:|---|
| `round432_delayed_exit_m150` | 10 bps | VT 8%, max 1.00 | 6.663% | +218.46% | 0.968 | 0.496 | -26.21% | none |
| `round433_delayed_exit_cost20_m150` | 20 bps | VT 8%, max 1.00 | 6.060% | +187.60% | 0.888 | 0.456 | -28.07% | none |
| `round433_delayed_exit_cost30_m150` | 30 bps | VT 8%, max 1.00 | 5.443% | +159.00% | 0.804 | 0.414 | -30.19% | user drawdown line breach |
| `round433_delayed_exit_cost30_vt075_max100_m150` | 30 bps | VT 7.5%, max 1.00 | 5.415% | +157.79% | 0.809 | 0.416 | -29.66% | none |

The 30 bps default risk budget narrowly breached the user's roughly -30% drawdown tolerance. A small volatility target cut from 8.0% to 7.5% brought drawdown back inside tolerance with minimal return loss.

## 30 Bps Risk-Budget Grid

This was a deliberately small risk-budget grid, not a new alpha search.

| Candidate | Annualized | Total Return | Sharpe | Overlap | Max DD | Leave-One-Year Min Ann. | Top 3 Month Share |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cost30_vt075_max100` | 5.415% | +157.79% | 0.809 | 0.416 | -29.66% | 3.67% | 55.28% |
| `cost30_vt075_max095` | 5.263% | +151.20% | 0.811 | 0.416 | -28.83% | 3.51% | 55.21% |
| `cost30_vt070_max100` | 5.293% | +152.45% | 0.807 | 0.415 | -29.11% | 3.54% | 55.55% |
| `cost30_vt070_max095` | 5.250% | +150.63% | 0.817 | 0.418 | -28.25% | 3.50% | 55.32% |
| `cost30_vt070_max090` | 5.093% | +143.99% | 0.819 | 0.418 | -27.43% | 3.33% | 55.27% |
| `cost30_vt065_max100` | 5.164% | +146.95% | 0.805 | 0.413 | -28.67% | 3.41% | 55.86% |
| `cost30_vt065_max095` | 5.165% | +147.02% | 0.818 | 0.419 | -27.63% | 3.41% | 55.62% |
| `cost30_vt065_max090` | 5.079% | +143.42% | 0.825 | 0.420 | -26.79% | 3.33% | 55.42% |

Decision: use `cost30_vt075_max100` as the high-cost stress fallback because it preserves the most return while respecting the drawdown tolerance.

## OOS And Block Checks

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass | Leave-One-Year Min Ann. | Leave-One-Year Min Overlap | Top 3 Month Share |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cost20` | 9.132% | 0.759 | -19.75% | 76.67% | 4.35% | 0.380 | 49.87% |
| `cost30_vt075` | 8.197% | 0.684 | -20.28% | 76.67% | 3.67% | 0.328 | 55.28% |

Both pass the block audit. OOS strict pass weakens versus the 10 bps delayed-exit candidate, so 20 bps and 30 bps should be treated as cost-stress lanes, not evidence that higher trading costs are harmless.

## Beta-Adjusted Check

| Candidate | ZZ500 Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged Max DD | Alpha t |
|---|---:|---:|---:|---:|---:|---:|
| `cost20` | 0.0479 | 0.270 | 6.744% | 0.724 | -14.14% | 3.97 |
| `cost30_vt075` | 0.0471 | 0.269 | 5.952% | 0.651 | -14.36% | 3.57 |

The cost-stressed candidates retain positive residual returns after ZZ500 beta adjustment.

## Handoff Decision

Promote the delayed-exit pack to the active paper-simulation handoff set:

- default 10 bps lane: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`;
- heavier-cost 20 bps lane: `paper_ready_delayed_exit_m150_cost20_vt08_max100_self_roll21_x08`;
- stress-fallback 30 bps lane: `paper_ready_delayed_exit_m150_cost30_vt075_max100_self_roll21_x08`.

The old Round425 handoff pack becomes a research reference because Round428 found an extreme-trade dependency and Round433 has now produced a cleaner delayed-exit replacement.

Remaining caveats for the simulation stage:

- OOS strict pass for cost20/cost30 is 76.67%, weaker than 10 bps.
- The 30 bps lane relies on a small risk-budget change, not an improved alpha signal.
- Best three months still contribute about 50% to 55% of total log return.
- Final holdout 2026 remains sealed.
