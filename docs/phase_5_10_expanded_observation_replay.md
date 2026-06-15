# Phase 5.10 Expanded Observation Replay

This phase turns the Phase 5.9 sample-size recommendation into a repeatable paper-only replay:

1. read the observation sufficiency pack;
2. stop immediately unless it recommends `extend_recent_data_window`;
3. rerun recent data refresh with the suggested start/end dates;
4. rerun post-refresh replay on the expanded data;
5. rerun observation sufficiency on the expanded replay result;
6. write one expanded observation replay decision pack.

It does not connect to a broker, read an account, place orders, or approve live trading.

## Command

Default real-state replay:

```powershell
python scripts\run_expanded_observation_replay.py --observation-sufficiency-pack data\reports\observation_sufficiency\observation_sufficiency_pack.json --report-dir data\reports\expanded_observation_replay
```

Fixture replay rehearsal:

```powershell
python scripts\run_expanded_observation_replay.py --observation-sufficiency-pack data\reports\observation_sufficiency_fixture\observation_sufficiency_pack.json --profile-observation-pack data\reports\profile_observation\profile_observation_pack.json --report-dir data\reports\expanded_observation_replay_fixture --source tushare-fixture
```

Outputs:

- `data/reports/expanded_observation_replay/expanded_observation_replay_pack.json`
- `data/reports/expanded_observation_replay/expanded_observation_replay_pack.md`
- `data/reports/expanded_observation_replay/expanded_observation_replay_next_actions.csv`

Fixture rehearsal also writes nested recent refresh, post-refresh replay, and final observation sufficiency packs under:

- `data/reports/expanded_observation_replay_fixture/recent_data_refresh`
- `data/reports/expanded_observation_replay_fixture/post_refresh_replay`
- `data/reports/expanded_observation_replay_fixture/observation_sufficiency`

## Current Result

Default real-state replay:

- stage: `phase_5_10_expanded_observation_replay`
- status: `blocked`
- blocker: `profile_observation_artifact_missing`
- reason: real recent Tushare refresh is still blocked before post-refresh observation exists.
- live boundary allowed: `false`

Fixture expanded replay:

- stage: `phase_5_10_expanded_observation_replay`
- status: `expanded_replay_blocked`
- expanded window: `2025-12-26` to `2026-06-13`
- recent data rows: `340`
- recent data coverage: `pass`
- observed fills after expansion: `15`
- required fills: `20`
- fill deficit after expansion: `5`
- final recommended start date: `2025-11-07`
- threshold relaxation allowed: `true`
- live boundary allowed: `false`

The fixture rehearsal proves that the expanded replay chain executes end to end. It also shows the strategy remains low-turnover: a roughly 162-day observation window still produced only 15 fills. The next decision is now explicit: extend once more to the recommended `2025-11-07` start date or manually review whether the early-stage min-fills policy should be adjusted.

To automate repeated extension before any threshold review, run:

```powershell
python scripts\run_iterative_observation_expansion.py --observation-sufficiency-pack data\reports\observation_sufficiency\observation_sufficiency_pack.json --report-dir data\reports\iterative_observation_expansion
```

## Policy

This phase is a replay mechanism, not a risk waiver.

- It only executes when Phase 5.9 recommends extending the data window.
- It preserves `threshold_policy=extend_window_before_relaxing_min_fills`.
- It records any remaining min-fills blocker instead of overriding it.
- It keeps `live_boundary_allowed=false` in every outcome.

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing this phase only means an expanded paper observation window cleared the sample gate. It is not permission to trade live.
