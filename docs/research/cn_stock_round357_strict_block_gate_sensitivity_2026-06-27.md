# CN Stock Round357 - Strict Block Gate Sensitivity

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round357 reruns the Round356 block-dependence audit with stricter pre-simulation gates.

This is a sensitivity check, not a new promotion rule.

Output:

`data/reports/round357_24h_profit_sprint_strict_shortlist_block_gate_sensitivity_20260627`

## Strict Gates

- Leave-one-year annualized return must be at least +3.00%.
- Leave-one-year overlap Sharpe must be at least 0.40.
- Top three months log-return share must be no more than 45.00%.
- 2026 final holdout remains sealed.

These gates are intentionally stricter than Round356 and are used to identify weak spots before simulation.

## Results

| Candidate | Ann. | Overlap Sharpe | Min Ann. After Removing One Year | Min Overlap After Removing One Year | Best 3 Months Log Share | Blockers |
|---|---:|---:|---:|---:|---:|---|
| `primary_high_return` | +6.35% | 0.517 | +3.76% | 0.386 | 46.38% | `weak_overlap_when_year_removed`; `best_months_contribution_too_high` |
| `primary_balanced_zz500_75` | +5.99% | 0.530 | +3.41% | 0.411 | 45.84% | `best_months_contribution_too_high` |
| `primary_defensive_zz500` | +5.62% | 0.536 | +3.05% | 0.435 | 46.66% | `best_months_contribution_too_high` |
| `safer_defensive_zz500` | +4.73% | 0.534 | +2.52% | 0.443 | 48.26% | `leave_one_year_annualized_return_below_min`; `best_months_contribution_too_high` |
| `primary_ps_filtered_defensive_zz500` | +4.86% | 0.573 | +2.74% | 0.492 | 43.75% | `leave_one_year_annualized_return_below_min` |

## Interpretation

No candidate passes this deliberately strict gate.

That does not invalidate Round356. It says the current family still has a visible 2015 contribution and should not be oversold as a smooth all-regime alpha.

Ranking under strict gates:

1. `primary_balanced_zz500_75`: only slightly above the concentration cutoff and keeps leave-one-year annualized return above 3%.
2. `primary_defensive_zz500`: best default robustness profile, but top-three-month concentration is still above 45%.
3. `primary_ps_filtered_defensive_zz500`: best concentration and overlap profile, but return floor after removing 2015 falls to +2.74%.
4. `safer_defensive_zz500`: lowest drawdown, but after the correct final overlay stream it fails both the +3% leave-one-year floor and the 45% concentration gate.
5. `primary_high_return`: best total return, but strict audit shows the clearest fragility after removing 2015.

## Direction Decision

Do not expand the shortlist just because Round357 blocks all five under harsh thresholds.

Use Round357 to refine simulation lanes:

- keep `primary_high_return` only as return-seeking/high-drawdown lane;
- keep `primary_balanced_zz500_75` as the return/risk middle lane;
- keep `primary_defensive_zz500` as the default robustness lane;
- keep `primary_ps_filtered_defensive_zz500` as a defensive diagnostic lane;
- de-emphasize `safer_defensive_zz500` unless the next stage needs an ultra-defensive benchmark.

Next work should create the Round356-358 audit and then prepare the Round359 package/push checkpoint.
