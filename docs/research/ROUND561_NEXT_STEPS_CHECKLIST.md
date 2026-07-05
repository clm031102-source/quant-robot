# Round561 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- H1 2024 daily-basic valuation shape/exposure audit completed.
- Raw quantile shape passed, but residual exposure audit failed.
- Residual IC turned significantly negative after industry/style controls.
- No candidate is promoted.

## Recommended Next Work

1. Add gate-packet traceability to the daily-basic valuation shape/exposure audit CLI, similar to alpha-factory manifests.
2. After that, rotate away from direct daily-basic valuation repair unless a preregistered orthogonal residual construction is supplied.
3. Consider a new PIT-safe source family for the next candidate plan.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Daily-basic valuation repair parameter widening.
- Portfolio-grid promotion from raw shape or raw IC.
- Final-holdout tuning.
