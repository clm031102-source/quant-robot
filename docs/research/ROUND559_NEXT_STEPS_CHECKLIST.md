# Round559 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- Alpha-factory summaries now include return-quality and capacity blocker counts.
- The change is covered by focused summary tests plus alpha-factory CLI/unit coverage.
- No new candidate is promoted.

## Recommended Next Work

1. Run the longer 2024 discovery-window daily-basic diagnostic with the same startup, data-manifest, and candidate-plan gate packets.
2. Record the new summary fields in the generated lightweight research note.
3. Add style-exposure diagnostics for size-like and value-like fields before considering any long-cycle replay.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Promotion claims from smoke evidence.
- Final-holdout tuning.
