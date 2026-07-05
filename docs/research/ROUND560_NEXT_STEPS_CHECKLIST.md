# Round560 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- The gated 2024 H1 daily-basic diagnostic completed 12 / 12 cases.
- All candidates had negative total return and negative Sharpe.
- Seven candidates had capacity-limited trades.
- No candidate is promoted.

## Recommended Next Work

1. Add a style-exposure/residual diagnostic for daily-basic fields if this family needs a failure-mode explanation.
2. Otherwise rotate to a new PIT-safe source family rather than widening daily-basic thresholds.
3. Keep the Round559 return/capacity summary fields in every future alpha-factory research note.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Promotion claims from H1 diagnostic evidence.
- Final-holdout tuning.
