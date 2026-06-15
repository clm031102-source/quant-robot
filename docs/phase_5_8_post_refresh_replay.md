# Phase 5.8 Post-Refresh Replay

This phase turns a successful recent-data refresh into a paper-only replay gate:

1. read the Phase 5.7 recent data refresh pack;
2. stop immediately if recent data is not ready;
3. rerun Daily Ops on the refreshed processed bars when recent data is ready;
4. rerun Profile Observation from the replayed Daily Ops simulation;
5. write a single post-refresh replay decision pack.

It does not connect to a broker, read an account, place orders, or approve live trading.

## Command

Default blocked-state replay:

```powershell
python scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\recent_data_refresh\recent_data_refresh_pack.json --report-dir data\reports\post_refresh_replay
```

Fixture replay rehearsal:

```powershell
python scripts\run_post_refresh_replay.py --recent-data-refresh-pack data\reports\recent_data_refresh_fixture\recent_data_refresh_pack.json --report-dir data\reports\post_refresh_replay_fixture
```

Outputs:

- `data/reports/post_refresh_replay/post_refresh_replay_pack.json`
- `data/reports/post_refresh_replay/post_refresh_replay_pack.md`
- `data/reports/post_refresh_replay/post_refresh_replay_next_actions.csv`

Fixture rehearsal also writes:

- `data/reports/post_refresh_replay_fixture/daily_ops`
- `data/reports/post_refresh_replay_fixture/profile_observation`

## Current Result

Default real Tushare replay:

- stage: `phase_5_8_post_refresh_replay`
- status: `blocked`
- recent data ready: `false`
- blocker: `TUSHARE_TOKEN is not set`
- live boundary allowed: `false`

Fixture replay rehearsal:

- stage: `phase_5_8_post_refresh_replay`
- status: `replay_blocked`
- recent data ready: `true`
- Daily Ops paper allowed: `true`
- profile observation allowed: `false`
- blocker: `minimum_fills_observed`
- fixture Daily Ops total return: `-1.7886%`
- fixture Daily Ops max drawdown: `-1.7886%`
- fixture processed rows: `46`
- live boundary allowed: `false`

The fixture rehearsal proves the post-refresh replay chain runs end to end. The next gate is not code execution; it is observation sufficiency. A 23-day fixture window only produced too few fills for the `min_fills=20` observation rule.

When replay is blocked by `minimum_fills_observed`, run:

```powershell
python scripts\run_observation_sufficiency.py --post-refresh-replay-pack data\reports\post_refresh_replay\post_refresh_replay_pack.json --output-dir data\reports\observation_sufficiency
```

## Decision Logic

The replay pack is `completed` only if all are true:

- recent data refresh has `recent_data_ready=true`;
- recent data refresh has `signal_data_stale_cleared=true`;
- Daily Ops returns `paper_trading_allowed=true`;
- Profile Observation returns `paper_observation_allowed=true`;
- no replay error is raised by downstream paper workflows.

Otherwise it records one of:

- `blocked`: recent refresh is not ready;
- `replay_blocked`: recent refresh ran, but Daily Ops or Profile Observation blocked continuation;
- `replay_failed`: a downstream paper workflow raised an execution error.

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing this phase only permits continued paper observation on refreshed data. It is not permission to trade live.
