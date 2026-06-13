# Phase 3.1 Data Quality Gap Audit Design

## Purpose

Phase 3.1 converts the aggregate CN ETF `missing_date_rows` blocker into exact asset/date rows and repair commands. The goal is to make the first Evidence Refresh action inspectable and repeatable.

## Scope

The feature audits local processed bars only. It does not fetch external data, infer exchange holidays, approve missing rows, or mutate datasets.

Out of scope:

- Provider calls.
- CSV backfill automation.
- Broker connectivity.
- Account reads.
- Order placement.

## Architecture

`quant_robot.data.gap_audit` owns pure audit logic. It accepts a normalized bars DataFrame and optional expected dates, then returns:

- summary counts;
- `missing_dates` rows with `asset_id`, `symbol`, and `missing_date`;
- coverage by asset;
- repair actions;
- Markdown output.

`scripts/run_data_quality_audit.py` owns filesystem concerns. It loads processed bars through `load_processed_bars()`, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the audit after `data_catalog` so local checks reveal exact gaps before running research workflows.

## Testing

Use unittest:

- `tests/unit/test_data_quality_gap_audit.py`
- `tests/unit/test_data_quality_gap_audit_cli.py`
- `tests/unit/test_evidence_refresh.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks and `scripts/run_checks.py --execute`.
