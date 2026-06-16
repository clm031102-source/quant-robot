# Phase 5.12 Tushare Activation Gate

## What changed

Phase 5.12 adds a local-only activation gate that chains the existing paper workflow:

1. Phase 5.7 recent data refresh
2. Phase 5.8 post-refresh replay
3. Phase 5.9 observation sufficiency
4. Phase 5.11 iterative observation expansion

The gate writes one auditable pack:

- `data/reports/tushare_activation_gate/tushare_activation_gate_pack.json`
- `data/reports/tushare_activation_gate/tushare_activation_gate_pack.md`
- `data/reports/tushare_activation_gate/tushare_activation_gate_stage_ledger.csv`
- `data/reports/tushare_activation_gate/tushare_activation_gate_next_actions.csv`

It is also exposed in the local GUI through `/api/risk/tushare-activation-gate`.

## Current real-data status

The real Tushare execute run now clears the paper-observation gate:

- Status: `paper_observation_ready`
- Source: `tushare`
- Mode: `execute`
- Tushare readiness: `true`
- Recent data ready: `true`
- Activation chain allowed: `true`
- Paper continuation allowed: `true`
- Final observation sufficiency: `sufficient`
- Final fills: `21 / 20`
- Iterative expansion: `completed` after 2 rounds
- Blockers: none
- Live boundary allowed: `false`

The real run uses the token only from the local process environment. Do not commit the token or paste it into docs.

Recent refresh still records full-provider data-quality warnings, including `226` provider-level missing date rows, but the activation decision is scoped to the observed advisory asset when available. The required asset `CN_ETF_XSHG_516160` covered the adjusted trading window from `2026-05-25` through `2026-06-12`, so the recent-data gate cleared.

The first post-refresh replay produced only `3 / 20` fills, so the chain expanded the observation window. Round 2 replay aligned the paper run date with the expanded window end, cleared `signal_data_stale`, and produced `21 / 20` fills.

## Fixture proof

The fixture run proves the activation chain behavior without network access:

- Status: `paper_observation_ready`
- Recent data ready: `true`
- Initial post-refresh replay: `replay_blocked`
- Initial blocker: `minimum_fills_observed`
- Iterative observation expansion: `completed`
- Final fills: `29 / 20`
- Paper continuation allowed: `true`
- Live boundary allowed: `false`

The important detail is that an initial `minimum_fills_observed` blocker is not treated as permanent if iterative expansion later clears the sample gate.

## Commands

Real readiness / execute attempt:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_activation_gate.py --machine highspec_desktop --report-dir data\reports\tushare_activation_gate --execute
```

Fixture execute:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_activation_gate.py --machine highspec_desktop --source tushare-fixture --report-dir data\reports\tushare_activation_gate_fixture --execute
```

Dry-run readiness check:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_activation_gate.py --machine laptop
```

When `--machine laptop` is selected, execute requests are stopped before the activation chain runs. The pack stays in dry-run mode and emits `handoff_tushare_activation_gate` with `highspec_desktop` and `office_desktop` as the data-pipeline workstations.

## Boundary

This stage is research-to-paper only. It does not connect to a broker, read account data, place orders, or approve live trading.

The next real step is continued paper observation and broader robustness validation. This gate is not permission to trade live.
