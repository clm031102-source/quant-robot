# CN Stock Rounds391-393 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Rounds Covered

| Round | Direction | Result | Promotion |
|---:|---|---|---:|
| 391 | Public indicators on Dragon-Hot official template | ADX bottom20 improved drawdown and overlap; SuperTrend and smart-money not worth expansion | 0 |
| 392 | Self-risk overlays on Dragon-Hot and ADX-on-Dragon | Self-risk rules gave larger risk improvement than new indicator names | 0 |
| 393 | Full-market public factor source rebuild | ADX signal replicated with cleaner source, but coverage blocker remains | 0 |

## Best Candidates After Audit

| Candidate | Role | Ann | Total | Overlap Sharpe | Max DD | Mean OOS Ann | Worst OOS DD | Key Caveat |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Dragon-Hot roll21 neg half | best current risk-budget lane | 6.71% | 1.9310 | 0.6172 | -15.46% | 7.20% | -12.75% | OOS return below raw Dragon-Hot |
| ADX full-source roll42 -3% half | new balanced observation | 6.51% | 1.8400 | 0.6386 | -17.41% | 7.70% | -13.86% | ADX missing share 34.04% |
| ADX full-source roll21 neg half | defensive reference | 6.48% | 1.8261 | 0.6613 | -13.78% | 6.92% | -11.42% | gives up OOS return |
| Dragon-Hot 100 | return reference | 6.45% | 1.8120 | 0.5324 | -28.57% | 8.02% | -23.68% | large drawdown |

## What Changed

This three-round block corrected an important process issue: public indicator files must not be borrowed from earlier subset experiments.

New required step before any public-indicator selected-entry filter:

`scripts/run_shortlist_public_factor_source.py`

Then use the generated `public_factor_values_for_shortlist.parquet` in:

`scripts/run_shortlist_public_factor_entry_filter.py`

## Direction Decision

Do not continue broad public-indicator parameter expansion.

Continue only two narrow threads:

- ADX as a defensive state filter around already-strong event lanes, but only after coverage repair;
- point-in-time self-risk overlays, because they directly improve drawdown, beta-adjusted overlap, and block stability without adding stock-selection degrees of freedom.

## Reject / Hibernate

- SuperTrend top/bottom grids: still dominated by missing coverage and old direct-signal failures.
- Smart-money public trend state: high missing share and no meaningful return improvement.
- KAMA/choppiness: useful as risk diagnostics, not enough return retention for shortlist.
- Anti-SuperTrend top20 from Round393: apparent projection improvement, but 83.60% missing-factor share means the sample is too selective.

## Next Work

The next mining block should rotate away from single public technical indicators and test one of:

- event timing around corporate events with strict announcement-date lag;
- industry-aware risk budget instead of hard industry filtering;
- capacity/cost stress on the current shortlist lanes;
- ETF-aware market regime profiles for simulation handoff.

The strongest current product direction is not "more factor names"; it is turning a small set of high-return CN stock event/risk lanes into simulation-ready, auditable return streams.
