# CN Stock Round346-348 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Rounds Reviewed

| Round | Work | Status |
|---:|---|---|
| 346 | Cost stress with fixed official vol-target exposure | Completed after correction |
| 347 | Benchmark beta audit | Completed after correction |
| 348 | Simulation shortlist packaging | Completed |

## Main Finding

The current candidate set is good enough to package for simulation-readiness review, but 2026 final holdout should still remain sealed until the project intentionally starts final validation.

## Corrections Made

Two first-pass outputs were superseded:

| Output | Problem | Replacement |
|---|---|---|
| `round346_24h_profit_sprint_cost_stress_primary_aggressive_20260627` | Recomputed vol-target exposure failed to reproduce official current-cost events | `round346_24h_profit_sprint_cost_stress_fixed_exposure_corrected_20260627` |
| `round347_24h_profit_sprint_benchmark_beta_audit_20260627` | Reported intercept-subtracted OLS residuals, which are near-zero mean by construction | `round347_24h_profit_sprint_benchmark_beta_audit_corrected_20260627` |

These corrections matter. Without them, the project would either understate the current candidate or misread beta-adjusted returns.

## Cost Stress Conclusion

Primary high-return candidate:

- at 10 bps: total +177.08%, overlap 0.517, max DD -28.88%;
- at 20 bps: total +152.60%, overlap 0.472, max DD -29.83%;
- at 30 bps: total +130.29%, overlap 0.427, max DD -30.77%, strict pass 63.33%.

Primary defensive candidate:

- at 10 bps: total +147.29%, overlap 0.536, max DD -20.38%;
- at 20 bps: total +130.44%, overlap 0.497, max DD -21.10%;
- at 30 bps: total +114.75%, overlap 0.457, max DD -21.81%, strict pass 90.00%.

Interpretation:

- high-return default is not cost-fragile, but quality degrades at 30 bps;
- defensive variant is materially more robust under higher cost assumptions.

## Beta Audit Conclusion

The current candidates are not just broad ETF beta.

Versus CSI500:

| Candidate | R2 | Hedged Ann. | Hedged Overlap | Hedged DD |
|---|---:|---:|---:|---:|
| `primary_high_return` | 0.251 | +6.32% | 0.826 | -13.40% |
| `primary_defensive_zz500` | 0.234 | +5.59% | 0.890 | -12.50% |
| `safer_defensive_zz500` | 0.212 | +4.69% | 0.861 | -8.10% |

Interpretation:

- benchmark dependence is moderate, not dominant;
- CSI500 explains more than HS300, consistent with the useful CSI500 regime overlay;
- beta-hedged diagnostics remain positive.

## Packaged Shortlist

Config:

`configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`

Runbook:

`docs/research/cn_stock_profit_sprint_simulation_shortlist_runbook_2026-06-27.md`

Shortlist:

1. `primary_high_return`
2. `primary_defensive_zz500`
3. `safer_defensive_zz500`

## Direction Audit

This is a productive direction.

The project now has:

- a concrete high-return candidate;
- a concrete defensive candidate;
- cost-stress evidence;
- capacity evidence;
- beta-dependence evidence;
- a repeatable config and runbook.

The next work should not blindly add new factor families until the current shortlist has a final pre-holdout checklist.

## Next Work

1. Create a final pre-holdout checklist.
2. Add a small consistency checker that confirms shortlist docs/config reference non-superseded outputs.
3. After one more round, package and push the Round340-349 work to GitHub under the 10-round rule.
4. Keep 2026 final holdout sealed unless explicitly entering final validation.
