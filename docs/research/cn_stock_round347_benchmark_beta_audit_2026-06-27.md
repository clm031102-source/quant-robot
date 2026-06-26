# CN Stock Round347 - Benchmark Beta Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round347 checks whether the current simulation candidates are mostly broad ETF beta.

Corrected output:

`data/reports/round347_24h_profit_sprint_benchmark_beta_audit_corrected_20260627`

Prior output:

`data/reports/round347_24h_profit_sprint_benchmark_beta_audit_20260627`

is superseded because it reported OLS residuals after subtracting the intercept. Those residuals have near-zero mean by construction and are not the right beta-hedged return stream.

Corrected method:

- estimate OLS beta with intercept for beta/R2 diagnostics;
- compute beta-hedged stream as `strategy_return - beta * benchmark_return`;
- do not subtract the intercept from the hedged stream.

Benchmarks:

- `CN_ETF_XSHG_510300` as HS300 proxy;
- `CN_ETF_XSHG_510500` as CSI500 proxy.

2026 final holdout remains unused.

## Result

| Candidate | Benchmark | Beta | R2 | Corr. | Strategy Ann. | Hedged Ann. | Hedged Overlap | Hedged DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `primary_high_return` | HS300 | 0.0478 | 0.197 | 0.444 | +6.35% | +6.56% | 0.696 | -29.52% |
| `primary_high_return` | CSI500 | 0.0403 | 0.251 | 0.501 | +6.35% | +6.32% | 0.826 | -13.40% |
| `primary_defensive_zz500` | HS300 | 0.0387 | 0.181 | 0.425 | +5.62% | +5.78% | 0.727 | -24.17% |
| `primary_defensive_zz500` | CSI500 | 0.0329 | 0.234 | 0.484 | +5.62% | +5.59% | 0.890 | -12.50% |
| `safer_defensive_zz500` | HS300 | 0.0319 | 0.172 | 0.415 | +4.73% | +4.85% | 0.725 | -18.81% |
| `safer_defensive_zz500` | CSI500 | 0.0265 | 0.212 | 0.460 | +4.73% | +4.69% | 0.861 | -8.10% |

## Interpretation

This is a materially better beta profile than earlier rejected CN stock lines that had R2 above 0.99.

Current candidates have moderate benchmark dependence:

- R2 versus HS300 is about 0.17-0.20;
- R2 versus CSI500 is about 0.21-0.25;
- CSI500 beta is the larger explanatory benchmark, which is consistent with the usefulness of the CSI500 momentum regime overlay.

The beta-hedged stream remains positive:

- primary high-return candidate hedged against CSI500: +6.32% annualized, overlap 0.826, max DD -13.40%;
- primary defensive candidate hedged against CSI500: +5.59% annualized, overlap 0.890, max DD -12.50%;
- safer defensive candidate hedged against CSI500: +4.69% annualized, overlap 0.861, max DD -8.10%.

These hedged diagnostics are not a live short-ETF strategy. They are evidence that the candidate is not merely broad market beta.

## Decision

Keep the three candidate tiers:

- high-return default: `primary_high_return`;
- preferred defensive: `primary_defensive_zz500`;
- ultra-defensive reference: `safer_defensive_zz500`.

The beta audit supports advancing them to final pre-holdout packaging.

Next work:

- formalize candidate configs/runbook entries;
- prepare a 2026 read-once holdout checklist;
- do not run the 2026 holdout until the project intentionally enters final validation.
