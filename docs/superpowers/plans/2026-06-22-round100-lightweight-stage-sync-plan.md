# Round100 Lightweight Stage Sync Plan - 2026-06-22

## Steps

1. Write the Round100 lightweight stage report.
2. Update startup gate to point at the post-sync research direction.
3. Run focused tests and project audit.
4. Run `scripts/sync_project.py --machine office_desktop --task factor_validation` in audit mode.
5. If the audit has no blockers or forbidden paths, run `scripts/sync_project.py --machine office_desktop --task factor_validation --execute --push`.
6. Report the commit and push outcome.

## Gate

Stop before push if `sync_project.py` reports forbidden paths, branch-behind status, validation failure, branch discovery failure, or non-syncable secret/data paths.
