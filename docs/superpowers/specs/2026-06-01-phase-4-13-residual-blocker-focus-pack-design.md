# Phase 4.13 Residual Blocker Focus Pack Design

## Objective

Create a local operations artifact that turns the Phase 4.12 readiness projection residuals into a prioritized focus pack. The pack must show which residual blocker classes should be attacked first, which existing blocker work items they cover, which downstream manual-review blockers are waiting on them, and which local commands should be run next.

## Scope

In scope:

- Consume `readiness_projection_pack.json`.
- Consume `blocker_resolution_worklist.json`.
- Prioritize residual tracks with remaining blockers.
- Link related work items and blocker IDs.
- Map downstream manual-review blockers back to upstream residual tracks.
- Write JSON, Markdown, and CSV artifacts.
- Add the CLI to the local check plan.

Out of scope:

- Mutating real readiness evidence.
- Installing provider dependencies.
- Setting tokens.
- Calling external market data providers.
- Connecting to brokers, reading accounts, placing orders, or enabling live trading.

## Inputs

- `data/reports/readiness_projection/readiness_projection_pack.json`
- `data/reports/blocker_worklist/blocker_resolution_worklist.json`

## Outputs

Directory: `data/reports/residual_blocker_focus/`

- `residual_blocker_focus_pack.json`
- `residual_blocker_focus_pack.md`
- `residual_focus_items.csv`
- `residual_downstream_waits.csv`
- `residual_focus_actions.csv`

## Data Model

Focus item fields:

- `focus_id`
- `priority_rank`
- `track_id`
- `label`
- `remaining_blockers`
- `projected_status`
- `projected_evidence`
- `current_status`
- `current_evidence`
- `source_stage`
- `linked_work_item_ids`
- `blocker_ids`
- `primary_commands`
- `downstream_blocker_ids`
- `local_only`

Downstream wait fields:

- `track_id`
- `blocked_by_tracks`
- `blocker_ids`
- `evidence`
- `local_only`

Action fields:

- `priority`
- `source_priority`
- `track_id`
- `command`
- `reason`
- `focus_track_id`
- `local_only`

## Prioritization

1. Include residual rows where `remaining_blockers > 0`.
2. Sort by `remaining_blockers` descending, preserving source order as a tie breaker.
3. Link related tracks:
   - `data_gap_resolution` also covers `data_quality`.
   - `provider_remediation` also covers `provider_readiness`.
4. Manual-review blockers are downstream waits when their blocker IDs mention missing dates, data quality, providers, or provider readiness.

## Safety

The pack is research-only. It is an operational planning artifact and must preserve the input boundary state. It must never connect to brokers, read accounts, place orders, enable live trading, set tokens, install dependencies, or call market data providers.
