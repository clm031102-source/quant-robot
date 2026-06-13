# Phase 4.15 Residual Provider Review Pack Design

## Objective

Create a local review pack for provider-remediation items that remain blocking after the Phase 4.11 provider-remediation rehearsal. This follows the Phase 4.13 focus pack, where `provider_remediation` is the second residual root track.

## Scope

In scope:

- Consume `provider_remediation_rehearsal.json`.
- Extract rehearsed remediation items where `blocks_provider_readiness` remains true.
- Write a residual review template that can be passed to `scripts/run_provider_remediation.py --review-file`.
- Write a local action queue for checking readiness, applying review rows, refreshing rehearsal, refreshing projection, and refreshing the residual focus pack.
- Add the CLI to the local check plan.

Out of scope:

- Installing provider dependencies.
- Setting credentials or tokens.
- Calling data providers.
- Connecting to brokers, reading accounts, placing orders, or enabling live trading.

## Inputs

- `data/reports/provider_remediation_rehearsal/provider_remediation_rehearsal.json`
- Optional: `data/reports/residual_blocker_focus/residual_blocker_focus_pack.json`

## Outputs

Directory: `data/reports/residual_provider_review/`

- `residual_provider_review_pack.json`
- `residual_provider_review_pack.md`
- `residual_provider_remediation_items.csv`
- `residual_provider_review_template.csv`
- `residual_provider_action_queue.csv`
- `residual_provider_status_options.csv`

## Data Model

Residual item fields:

- `remediation_id`
- `provider`
- `blocker_type`
- `blocker`
- `review_status`
- `evidence_note`
- `verification_command`
- `resolution_hint`
- `blocks_provider_readiness`
- `local_only`

Template row fields:

- `remediation_id`
- `provider`
- `blocker_type`
- `blocker`
- `review_status`
- `evidence_note`
- `reviewed_by`
- `reviewed_at`
- `verification_command`
- `resolution_hint`
- `allowed_statuses`
- `review_guidance`

## Safety

This pack is research-only. It prepares local review rows and commands only. It must not install packages, set tokens, call providers, connect to brokers, read accounts, place orders, or enable live trading.
