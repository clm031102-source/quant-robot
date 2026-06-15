# Phase 3.5 Manual Review Gate Rehearsal Design

## Purpose

Phase 3.5 converts the blocked manual review gate into an explicit local dry run. The goal is to list every clean-state requirement while proving the rehearsal does not connect to brokers, read accounts, place orders, or enable live trading.

## Scope

The feature reads local review and evidence artifacts only. It does not change promotion thresholds, enable live review, connect to providers, connect to brokers, read accounts, or place orders.

Out of scope:

- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.
- Provider API calls.

## Architecture

`quant_robot.ops.manual_review_rehearsal` owns pure gate logic. It accepts a promotion review packet plus optional data-quality, provider-evidence, paper-observation, and duplicate-registry evidence, then returns:

- gate status;
- blockers;
- requirement rows;
- dry-run boundary state;
- Markdown output.

`scripts/run_manual_review_rehearsal.py` owns filesystem concerns. It reads local evidence artifacts, writes JSON/Markdown/CSV outputs, and prints a compact summary.

`scripts/run_checks.py` includes the rehearsal after Promotion Review.

`quant_robot.ops.evidence_refresh` recommends `run_manual_review_rehearsal.py` while the manual-review gate remains blocked.

## Testing

Use unittest:

- `tests/unit/test_manual_review_rehearsal.py`
- `tests/unit/test_manual_review_rehearsal_cli.py`
- `tests/unit/test_evidence_refresh.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks, artifact generation, and `scripts/run_checks.py --execute`.
