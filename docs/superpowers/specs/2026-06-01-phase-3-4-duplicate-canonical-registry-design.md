# Phase 3.4 Duplicate Canonical Registry Design

## Purpose

Phase 3.4 converts duplicate suppression from transient promotion-report fields into a stable registry. The goal is to make canonical candidates and suppressed duplicate members inspectable across CLI artifacts, Promotion Ops, and Review Packets.

## Scope

The feature reads local promotion-report artifacts only. It does not rerun research, alter promotion thresholds, connect to brokers, read accounts, or place orders.

Out of scope:

- Changing duplicate-similarity logic.
- Re-ranking candidates.
- Broker connectivity.
- Account reads.
- Order placement.

## Architecture

`quant_robot.ops.duplicate_registry` owns pure registry logic. It accepts a promotion report and returns:

- summary counts;
- canonical candidate rows;
- duplicate member rows;
- Markdown output.

`scripts/run_duplicate_registry.py` owns filesystem concerns. It reads `promotion_report.json`, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the registry after Promotion Ops.

`quant_robot.ops.evidence_refresh` recommends `run_duplicate_registry.py` during duplicate-resolution work.

`quant_robot.ops.promotion_console` embeds the registry summary and rows in the Promotion Ops payload, and `quant_robot.ops.review_packet` carries the summary into review packets.

## Testing

Use unittest:

- `tests/unit/test_duplicate_registry.py`
- `tests/unit/test_duplicate_registry_cli.py`
- `tests/unit/test_promotion_ops.py`
- `tests/unit/test_promotion_review_packet.py`
- `tests/unit/test_evidence_refresh.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks, artifact generation, and `scripts/run_checks.py --execute`.
