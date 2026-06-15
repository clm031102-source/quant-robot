# Phase 4.14 Residual Data Gap Review Pack Design

## Objective

Create a local review pack for data gaps that remain blocking after the Phase 4.6 data-gap rehearsal. This directly follows the Phase 4.13 focus pack, where `data_gap_resolution` is the highest-priority residual track.

## Scope

In scope:

- Consume `data_gap_rehearsal.json`.
- Extract rehearsed ledger rows where `blocks_api_boundary` remains true.
- Write a residual review template that can be passed to `scripts/run_data_gap_resolution.py --resolution-file`.
- Write a local action queue for reviewing, refreshing, and applying residual gap evidence.
- Add the CLI to the local check plan.

Out of scope:

- Mutating the real data-gap ledger.
- Importing or downloading external data.
- Calling market data APIs.
- Connecting to brokers, reading accounts, placing orders, or enabling live trading.

## Inputs

- `data/reports/data_gap_rehearsal/data_gap_rehearsal.json`
- Optional: `data/reports/residual_blocker_focus/residual_blocker_focus_pack.json`

## Outputs

Directory: `data/reports/residual_data_gap_review/`

- `residual_data_gap_review_pack.json`
- `residual_data_gap_review_pack.md`
- `residual_data_gap_rows.csv`
- `residual_gap_review_template.csv`
- `residual_gap_action_queue.csv`
- `residual_gap_status_options.csv`

## Data Model

Residual row fields:

- `gap_id`
- `asset_id`
- `symbol`
- `missing_date`
- `resolution_status`
- `evidence_note`
- `recommended_command`
- `blocks_api_boundary`
- `local_only`

Template row fields:

- `gap_id`
- `asset_id`
- `symbol`
- `missing_date`
- `resolution_status`
- `evidence_note`
- `reviewed_by`
- `reviewed_at`
- `allowed_statuses`
- `review_guidance`

## Safety

This pack is research-only. It prepares local review rows and commands only. It must not import data, call providers, set tokens, connect to brokers, read accounts, place orders, or enable live trading.
