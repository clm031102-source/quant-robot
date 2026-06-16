# Factor Branch Sync Integration Design

## Goal

Make useful factor-research work produced on any workstation discoverable, reviewable, and alignable through the normal `同步项目` workflow without treating exploratory results as deployable trading signals.

## Scope

This design integrates the useful code, configs, tests, and lightweight research notes from `origin/codex/factor-batch-moneyflow-alpha` into the core repository. It also strengthens `scripts/sync_project.py` so each sync audit can identify remote factor, validation, review, or integration branches whose commits have not yet been recorded as absorbed by core code.

The sync workflow must continue to exclude local data products, generated reports, credentials, logs, account data, broker data, and any live-trading capability.

## Architecture

The core repository remains the shared source of truth for reusable research code. Workstations may still produce exploratory branches, but useful work must be copied or merged into a core branch and recorded in a lightweight integration manifest before being considered aligned.

The sync script will load a manifest under `configs/` and compare its absorbed commits against remote research branches. In audit mode it reports pending branches; in execute mode for `architecture_ops`, `factor_integration`, or `project_sync`, pending branches block push unless explicitly recorded as ignored or absorbed.

## Components

- `configs/factor_branch_integration_manifest.json` records absorbed and ignored branch heads.
- `scripts/sync_project.py` classifies local changed paths and also audits remote research branches.
- `tests/unit/test_sync_project.py` covers sync path safety and pending-branch blockers.
- The moneyflow branch contributes reusable factor, input, alpha-factory, walk-forward, archive-replay, and safety-gate modules.
- Lightweight docs record what was integrated and what remains only a candidate.

## Data Flow

1. A workstation pushes a task branch such as `codex/factor-batch-moneyflow-alpha`.
2. Another workstation runs `同步项目`, which calls `scripts/sync_project.py`.
3. The script fetches `origin`, lists remote research branches, and compares their HEAD commits with the manifest and current branch history.
4. If useful work is pending, the audit reports it; execute/push mode blocks core sync until the branch is integrated or explicitly recorded.
5. Once integrated, the manifest stores the branch name, commit, status, summary, and integration date.

## Error Handling

The sync script should be conservative. Missing manifest files are allowed and mean no absorbed branch records exist yet. Git command failures in branch discovery should return a diagnostic audit field rather than crashing audit mode. Execute mode should block when pending branches or forbidden paths are present.

## Testing

Tests must prove that:

- Known absorbed branch commits are not reported as pending.
- Remote research branches missing from the manifest are reported as pending.
- Core sync execute/push mode blocks when pending research branches exist.
- Normal factor-batch branch sync remains allowed so a workstation can still publish exploratory work for later review.

## Safety

This integration remains research-to-paper only. No broker connection, live account reads, order placement, automatic live trading, tokens, raw data, processed data, generated report outputs, or large artifacts are added.
