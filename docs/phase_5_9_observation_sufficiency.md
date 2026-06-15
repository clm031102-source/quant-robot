# Phase 5.9 Observation Sufficiency

This phase plans the sample-size gate after post-refresh replay.

It does not loosen risk controls automatically. If Profile Observation stops on `minimum_fills_observed`, the planner estimates how much more observation data is needed and recommends expanding the recent-data refresh window before any threshold relaxation is considered.

## Command

Default real-state planner:

```powershell
python scripts\run_observation_sufficiency.py --post-refresh-replay-pack data\reports\post_refresh_replay\post_refresh_replay_pack.json --output-dir data\reports\observation_sufficiency
```

Fixture planner:

```powershell
python scripts\run_observation_sufficiency.py --post-refresh-replay-pack data\reports\post_refresh_replay_fixture\post_refresh_replay_pack.json --output-dir data\reports\observation_sufficiency_fixture
```

Outputs:

- `data/reports/observation_sufficiency/observation_sufficiency_pack.json`
- `data/reports/observation_sufficiency/observation_sufficiency_pack.md`
- `data/reports/observation_sufficiency/observation_sufficiency_next_actions.csv`

## Current Result

Default real-state planner:

- stage: `phase_5_9_observation_sufficiency`
- status: `blocked_missing_observation`
- blocker: `profile_observation_artifact_missing`
- reason: real recent Tushare refresh is still blocked by missing local `TUSHARE_TOKEN`, so post-refresh observation has not run.

Fixture planner:

- stage: `phase_5_9_observation_sufficiency`
- status: `needs_more_observation_data`
- observed fills: `2`
- required fills: `20`
- fill deficit: `18`
- observation days: `17`
- fill rate per day: `0.117647`
- estimated total observation days: `170`
- additional observation days: `153`
- suggested start date: `2025-12-26`
- suggested end date: `2026-06-13`
- threshold relaxation allowed: `false`

## Policy

The planner follows this order:

1. extend the data and observation window;
2. rerun recent refresh;
3. rerun post-refresh replay;
4. only then review whether the min-fills policy itself needs a manual adjustment.

When the planner recommends `extend_recent_data_window`, run:

```powershell
python scripts\run_expanded_observation_replay.py --observation-sufficiency-pack data\reports\observation_sufficiency\observation_sufficiency_pack.json --report-dir data\reports\expanded_observation_replay
```

Automatic threshold relaxation is intentionally disabled unless the observed fills are near the threshold and no other stop rule is active. The current fixture has only `2` fills, so relaxing the threshold would be a tiny-sample shortcut and is not allowed.

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing this phase only means the paper observation sample is large enough under the current rule. It is not permission to trade live.
