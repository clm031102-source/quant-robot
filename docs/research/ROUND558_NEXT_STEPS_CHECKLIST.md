# Round558 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- The January 2024 daily-basic smoke has been rerun with startup, data-manifest, and candidate-plan gate packets.
- `manifest.json` now records all three gate packet paths.
- No candidate is promoted.
- Internal eligible rows are not promotion evidence because short-window portfolio returns are poor.

## Recommended Next Work

1. Run a longer 2024 discovery-window diagnostic with the same gate packets.
2. Add an explicit style-exposure report for size-like and value-like daily-basic fields.
3. Add capacity blocker summaries to the lightweight doc output before considering any long-cycle replay.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Promotion claims from smoke evidence.
- Final-holdout tuning.
