# Phase 3.0 Evidence Refresh Design

## Purpose

Phase 3.0 converts a blocked promotion review packet into a concrete local work queue. The goal is to make every blocker actionable without weakening the research-only boundary.

## Scope

The feature consumes a Phase 2.9 review packet and emits a refresh plan with tracks and ordered actions. It does not run those actions automatically, download data, connect to providers, or enable manual live review.

Out of scope:

- Broker connectivity.
- Account reads.
- Order placement.
- Live-trading approval.
- Automatic package installation or token configuration.

## Architecture

`quant_robot.ops.evidence_refresh` owns the pure planning logic. It reads review packet fields such as `checklist`, `manual_review_gate`, `duplicate_clusters`, and `evidence`, then emits:

- `tracks`: data quality, provider readiness, paper observation, duplicate resolution, and manual review gate.
- `ordered_actions`: local commands and reasons in the order an operator should address them.
- `markdown`: a human-readable refresh plan.

`scripts/run_evidence_refresh.py` owns filesystem concerns. The GUI calls the same service through `build_evidence_refresh_snapshot()` and `/api/promotion/evidence-refresh`.

## Status Rules

- Missing selected candidate -> `refresh_status=blocked`.
- Any track with `action_required`, `continue`, or `blocked` -> `refresh_status=action_required`.
- All tracks clear -> `refresh_status=clear`.

Track rules:

- `data_quality` is action-required when the review checklist blocks data quality.
- `provider_readiness` is action-required when providers are not ready.
- `paper_observation` is continue when the selected candidate is paper-ready or paper evidence passed.
- `duplicate_resolution` is action-required when the selected candidate has duplicate clusters.
- `manual_review_gate` remains blocked until the review packet allows manual review.

## Testing

Use unittest with red-green implementation:

- `tests/unit/test_evidence_refresh.py`
- `tests/unit/test_evidence_refresh_cli.py`
- `tests/unit/test_check_plan.py`
- `tests/unit/test_gui.py`

Full verification also requires compile checks, JS syntax checks, `run_checks.py --execute`, and browser verification of the Promotion Ops page.
