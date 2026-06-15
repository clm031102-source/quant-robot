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

The real Tushare run remains blocked at readiness:

- Status: `blocked_missing_readiness`
- Blocker: `TUSHARE_TOKEN is not set`
- Recent data ready: `false`
- Paper continuation allowed: `false`
- Live boundary allowed: `false`

This means the project still has not executed a real Tushare download in this environment. The raw token must be set locally as an environment variable before a real execute run can proceed.

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
.\.venv\Scripts\python.exe scripts\run_tushare_activation_gate.py --report-dir data\reports\tushare_activation_gate --execute
```

Fixture execute:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_activation_gate.py --source tushare-fixture --report-dir data\reports\tushare_activation_gate_fixture --execute
```

Dry-run readiness check:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_activation_gate.py
```

## Boundary

This stage is research-to-paper only. It does not connect to a broker, read account data, place orders, or approve live trading.

The next real step is to set `TUSHARE_TOKEN` in the local environment and rerun the activation gate. After that, the system should decide from artifacts whether paper observation can continue on real refreshed data.
