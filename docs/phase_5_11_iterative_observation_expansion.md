# Phase 5.11 Iterative Observation Expansion

This phase automates repeated expanded-window paper replays until the observation sample gate clears or a configured round limit is reached.

It does not connect to a broker, read an account, place orders, relax thresholds automatically, or approve live trading.

## Command

Default real-state run:

```powershell
python scripts\run_iterative_observation_expansion.py --observation-sufficiency-pack data\reports\observation_sufficiency\observation_sufficiency_pack.json --report-dir data\reports\iterative_observation_expansion
```

Fixture rehearsal:

```powershell
python scripts\run_iterative_observation_expansion.py --observation-sufficiency-pack data\reports\observation_sufficiency_fixture\observation_sufficiency_pack.json --profile-observation-pack data\reports\profile_observation\profile_observation_pack.json --report-dir data\reports\iterative_observation_expansion_fixture --source tushare-fixture --max-rounds 3
```

Outputs:

- `data/reports/iterative_observation_expansion/iterative_observation_expansion_pack.json`
- `data/reports/iterative_observation_expansion/iterative_observation_expansion_pack.md`
- `data/reports/iterative_observation_expansion/iterative_observation_expansion_rounds.csv`
- `data/reports/iterative_observation_expansion/iterative_observation_expansion_next_actions.csv`

Each round writes a full Phase 5.10 replay bundle under `round_01`, `round_02`, and so on.

## Current Result

Default real-state run:

- stage: `phase_5_11_iterative_observation_expansion`
- status: `blocked`
- round count: `0`
- blocker: `profile_observation_artifact_missing`
- reason: real Tushare refresh has not executed yet, so real post-refresh observation and sufficiency artifacts are not extendable.
- live boundary allowed: `false`

Fixture rehearsal:

- stage: `phase_5_11_iterative_observation_expansion`
- status: `completed`
- round count: `2`
- max rounds: `3`
- initial fills: `2 / 20`
- round 1: `15 / 20`, still blocked by `minimum_fills_observed`
- round 2: `29 / 20`, sample gate cleared
- final observation status: `sufficient`
- live boundary allowed: `false`

This proves the sample gate can be cleared by expanding the observation window without relaxing `min_fills`.

## Policy

The iterative runner follows these rules:

- Only run when Phase 5.9 recommends `extend_recent_data_window`.
- Stop immediately if the sufficiency artifact is missing or not extendable.
- Stop when sample sufficiency clears.
- Stop at `--max-rounds` before considering any policy relaxation.
- Keep every step local and paper-only.

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing this phase only means the paper observation sample is large enough under the current rule. It is not permission to trade live.
