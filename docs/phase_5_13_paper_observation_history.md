# Phase 5.13 Paper Observation History

Phase 5.13 turns one-off activation-gate results into a durable paper-only observation ledger.

It does not download market data, connect to a broker, read accounts, place orders, or approve live trading. It only reads existing Phase 5.12 activation gate packs and writes a history artifact.

## Command

```powershell
python scripts\run_paper_observation_history.py --activation-gate-pack data\reports\tushare_activation_gate\tushare_activation_gate_pack.json --output-dir data\reports\paper_observation_history
```

Multiple gate packs can be supplied by repeating `--activation-gate-pack`.

Outputs:

- `data/reports/paper_observation_history/paper_observation_history_pack.json`
- `data/reports/paper_observation_history/paper_observation_history_pack.md`
- `data/reports/paper_observation_history/paper_observation_history_ledger.csv`
- `data/reports/paper_observation_history/paper_observation_history_next_actions.csv`

## Current Result

- stage: `phase_5_13_paper_observation_history`
- run count: `1`
- paper-observation-ready runs: `1`
- blocked runs: `0`
- latest status: `paper_observation_ready`
- latest required asset: `CN_ETF_XSHG_516160`
- latest fills: `21 / 20`
- latest provider missing date rows: `226`
- history clear for continued paper observation: `true`
- live boundary violations: `0`
- live boundary allowed: `false`

## Decision Logic

The history pack clears continued paper observation only when:

- at least one activation gate run exists;
- the latest run is `paper_observation_ready`;
- the latest run has no blockers;
- the latest run allows paper continuation;
- no run reports `live_boundary_allowed=true`.

Any live-boundary violation immediately blocks the history pack, even if the latest paper gate otherwise looks clear.

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing this phase means the paper evidence ledger is clear enough to continue accumulating paper-only evidence. It is not permission to trade live.
