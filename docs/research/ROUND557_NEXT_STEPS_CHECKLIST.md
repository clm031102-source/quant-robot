# Round557 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- CN processed-bars alpha-factory runs require startup, data-manifest, and candidate-plan gate packets.
- The returned result and `manifest.json` now record all three gate packet paths.
- Tests cover missing candidate-plan packets, factor-name drift, and manifest trace writing.

## Recommended Next Work

1. Rerun the January 2024 daily-basic smoke with `--candidate-plan-gate-packet` so the generated manifest includes `gate_packets`.
2. Run a longer discovery-window daily-basic diagnostic only after confirming the generated manifest contains the gate trace.
3. Keep generated reports out of Git and record only lightweight summaries.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Promotion claims from smoke evidence.
- Final-holdout tuning.
