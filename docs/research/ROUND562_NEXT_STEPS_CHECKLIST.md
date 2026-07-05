# Round562 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- Daily-basic valuation shape/exposure audit output now records gate packet paths.
- Real H1 2024 diagnostic was rerun with startup, data-manifest, and candidate-plan packet traces.
- The daily-basic valuation repair family remains rejected.

## Recommended Next Work

1. Run a three-round review package for Rounds 560-562 before starting a new factor family.
2. Rotate away from direct daily-basic valuation repair unless a new preregistered residual construction is supplied.
3. Prepare the next PIT-safe source-family candidate plan.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Daily-basic valuation repair parameter widening.
- Portfolio-grid promotion from raw shape or raw IC.
- Final-holdout tuning.
