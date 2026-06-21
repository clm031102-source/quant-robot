# CN Stock Profitability Quality Family Rejection Audit Round99 - 2026-06-22

## Executive Summary

Round99 audited the Round97-99 profitability-quality work block after Round98 produced zero multiple-testing leads.

Decision: hibernate the current profitability-quality family and rotate after the required Round100 safe sync.

- Family: `financial_profitability_quality`
- Candidates audited: 14
- Factor-horizon tests audited: 28
- IC observations: 1,204
- Label-aligned rows: 117,394
- Bonferroni significant: 0
- FDR significant: 0
- Research leads: 0
- Audit requirements passed: 6/6
- Family hibernated: true
- Continue same family: false
- Immediate next direction: `round100_lightweight_stage_report_and_github_safe_sync`
- Post-sync research direction: `capacity_safe_price_volume_lowvol_reversal_composite_preregistration`

## Reject Reasons

- `zero_multiple_testing_leads`
- `zero_bonferroni_significant_results`
- `portfolio_backtest_not_allowed_after_ic_failure`

## Interpretation

The failure is not a data-alignment failure. The path from Tushare `fina_indicator` ingestion to PIT signal dating to controlled IC worked. The factor family itself did not show enough predictive signal on the clean 100-symbol shard to justify portfolio backtesting, full-universe expansion, or parameter tuning.

This is exactly where prior work went wrong: a weak family would continue into more grids. Round99 blocks that behavior.

## Public Reference Review

The next direction follows public-reference discipline:

- qlib-style separation of data, factor generation, IC analysis, and portfolio simulation.
- Alphalens-style IC, quantile spread, turnover, and decay diagnostics before portfolio expansion.
- vectorbt-style fast portfolio grids only after a signal survives pre-registered statistical screens.
- pyfolio-style risk attribution only after real portfolio evidence exists.
- WorldQuant-style simple price-volume transforms with explicit economic intuition rather than same-family tuning.

## Decision

Do not continue profitability-quality mining right now.

Next immediate step:

```text
round100_lightweight_stage_report_and_github_safe_sync
```

Post-sync research direction:

```text
capacity_safe_price_volume_lowvol_reversal_composite_preregistration
```
