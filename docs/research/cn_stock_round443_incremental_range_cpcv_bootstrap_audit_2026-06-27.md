# CN Stock Round443 Incremental Range CPCV/Bootstrap Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round443 tests whether the Round442 `range_contraction_lowvol_reversal_20` overlay has broad incremental value over the delayed-exit baseline, rather than only improving one full-sample line.

The audit uses:

- 10 chronological CPCV blocks, 3 held out per split, for 120 split combinations;
- 1,000 quarterly block-bootstrap paths;
- the same event-return annualization convention used by the project, `252 / 5`, with 20-period overlap correction.

## Result

| Case | Delta Ann. | Delta Total | Delta Overlap | Inc. Max DD | Year Win | CPCV Ann Win | CPCV Strict | Bootstrap Ann+ | Bootstrap Overlap+ | Bootstrap DD<=30% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `cost10` | +0.419% | +23.24% | +0.009 | -26.99% | 81.82% | 90.83% | 67.50% | 99.30% | 88.40% | 57.90% |
| `cost20` | +0.398% | +20.03% | +0.010 | -28.87% | 81.82% | 90.00% | 67.50% | 99.00% | 92.00% | 55.80% |
| `cost30` | +0.166% | +7.38% | +0.006 | -29.97% | 63.64% | 68.33% | 60.00% | 86.00% | 72.50% | 53.40% |

Output pack:

- `data/reports/round443_24h_profit_sprint_incremental_range_cpcv_bootstrap_audit_20260627/round443_case_summary.csv`
- `data/reports/round443_24h_profit_sprint_incremental_range_cpcv_bootstrap_audit_20260627/round443_cpcv_splits.csv`
- `data/reports/round443_24h_profit_sprint_incremental_range_cpcv_bootstrap_audit_20260627/round443_block_bootstrap.csv`
- `data/reports/round443_24h_profit_sprint_incremental_range_cpcv_bootstrap_audit_20260627/round443_yearly_delta.csv`

## Interpretation

The 10 bps lane is worth keeping as a return-seeking simulation-observation candidate. It has strong bootstrap positive-return evidence and broad CPCV annualized-return wins.

The main weakness is risk concentration. In the quarterly bootstrap, the incremental lane keeps drawdown within 30% only 57.90% of paths for 10 bps and 55.80% for 20 bps. That means the factor is not a clean risk reducer; it is a return enhancer with material drawdown-path sensitivity.

The 30 bps lane is too close to the drawdown limit and has a much smaller incremental return. It should remain a stress fallback only.

## Decision

Keep `incremental_range_cost10` on the active simulation-observation watchlist, but do not call it final alpha.

Carry `incremental_range_cost20` as a heavy-cost monitoring lane.

Treat `incremental_range_cost30_vt070` only as stress evidence.

The corrected Round442 FDR result still stands: final statistical candidates remain zero. Round443 improves confidence that the lead deserves continued work, not that it is ready for live or final paper promotion.
