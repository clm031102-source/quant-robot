# Round99 Profitability Quality Family Rejection Audit Design - 2026-06-22

## Objective

Close the Round97-99 block by auditing the profitability-quality family after the Round98 controlled IC screen produced zero multiple-testing leads.

The audit must decide whether to continue the same family, hibernate it, or rotate direction. It must also respect the ten-round sync cadence by routing the next immediate step to Round100 packaging and GitHub safe sync.

## Inputs

- Controlled IC result: `data/reports/profitability_quality_controlled_ic_screen_round98_20260622/profitability_quality_controlled_ic_screen.json`
- Source report: `docs/research/cn_stock_profitability_quality_controlled_ic_screen_round98_2026-06-22.md`
- Review rounds: 97, 98, 99

## Required Checks

- The controlled IC screen must have passed its own readiness checks.
- Multiple-testing metadata must exist.
- Bonferroni and FDR significant counts must be inspected.
- Portfolio promotion must remain blocked after IC failure.
- The review must cover exactly three consecutive rounds.
- The next action must respect the Round100 GitHub safe-sync cadence.

## Decision Logic

If the screen has zero FDR leads and no Bonferroni-significant result, hibernate the profitability-quality family and reject same-family tuning.

If a lead exists after multiple testing, do not reject the family; route it to robustness and portfolio-translation audit.

## Post-Sync Research Direction

After Round100 safe sync, rotate to:

```text
capacity_safe_price_volume_lowvol_reversal_composite_preregistration
```

This direction uses public-reference discipline: qlib-style separated data/factor/evaluation stages, Alphalens-style IC and quantile diagnostics, vectorbt-style portfolio grids only after statistical leads, and simple WorldQuant-like price-volume transforms with explicit economic intuition.
