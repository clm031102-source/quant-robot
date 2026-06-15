# Phase 5.6 Profile Observation Ledger

This phase turns the activated paper profile into an auditable observation ledger.

It does not connect to a broker, read an account, or place orders. It decides whether the current paper profile is allowed to keep observing, and records every stop rule that would block the next paper-observation cycle.

## Command

```powershell
python scripts\run_profile_observation.py --daily-ops-pack data\reports\daily_ops\daily_ops_pack.json --simulation-dir data\reports\daily_ops\paper_simulation --output-dir data\reports\profile_observation --run-date 2026-06-14
```

Outputs:

- `data/reports/profile_observation/profile_observation_pack.json`
- `data/reports/profile_observation/profile_observation_pack.md`
- `data/reports/profile_observation/profile_observation_ledger.csv`
- `data/reports/profile_observation/profile_observation_stop_rules.csv`
- `data/reports/profile_observation/profile_observation_next_actions.csv`

## Current Result

- stage: `phase_5_6_profile_observation_ledger`
- run date: `2026-06-14`
- candidate: `CN_ETF_liquidity_10_top1_cost5_reb5`
- profile: `cap60_guard12_cd3`
- risk tier: `aggressive_growth`
- observation status: `stopped`
- paper observation allowed: `false`
- live boundary allowed: `false`
- stop count: `1`
- warning count: `1`

The hard stop is `signal_data_stale`:

- signal date: `2026-05-22`
- run date: `2026-06-14`
- signal age: `23` calendar days
- max allowed signal age: `7` calendar days

The warning is `guard_event_ratio_high`:

- guard events: `712`
- equity points: `702`
- guard event ratio: `1.014245`
- warning threshold: `0.5`

Risk tier drawdown is still within the current aggressive-growth policy:

- max equity drawdown: `-25.2031%`
- active drawdown limit: `-30.0000%`
- rule status: `pass`

## Tushare Point

Tushare becomes useful now, not for live trading, but for refreshing recent CN ETF bars so the paper profile can be observed on current data.

Next local action from the pack:

```powershell
python scripts\ingest_data.py --source tushare --market CN_ETF --start-date 2026-05-23 --end-date 2026-06-14 --output-dir data\processed\tushare_etf_recent
```

After that refresh, rerun the data processing, daily ops, and profile observation steps. The expected outcome is that `signal_data_stale` clears or is replaced by a more concrete data-quality blocker.

## GUI/API

The local GUI now exposes this phase through:

- `GET /api/risk/profile-observation`
- Daily Ops page input: `Profile observation pack`
- Daily Ops panels: `Profile Observation`, `Stop Rules`, `Observation Ledger`, and `Observation Actions`
- Dashboard metric/status row: `Observation`

## Safety Boundary

This phase remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

No stop-rule pass should be interpreted as permission to trade live. Passing this ledger only means the profile may continue paper observation.

