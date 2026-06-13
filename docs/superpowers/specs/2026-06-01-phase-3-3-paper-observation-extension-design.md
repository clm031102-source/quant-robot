# Phase 3.3 Paper Observation Extension Design

## Purpose

Phase 3.3 converts local paper-batch output into a reviewable observation pack. The goal is to make `paper_ready` mean more than "one matching manifest exists" by surfacing observation windows, guard events, execution-block events, risk-profile comparison, and metric trends.

## Scope

The feature reads local paper-batch artifacts only. It does not run provider calls, connect to brokers, read accounts, place orders, or change promotion thresholds.

Out of scope:

- Broker connectivity.
- Account reads.
- Order placement.
- Live approval.
- Automatic paper-batch reruns.

## Architecture

`quant_robot.ops.paper_observation` owns pure aggregation logic. It accepts a paper-batch summary and optional candidate artifacts, then returns:

- summary counts;
- candidate observation rows;
- risk-profile comparison rows;
- metric trend rows;
- Markdown output.

`scripts/run_paper_observation.py` owns filesystem concerns. It reads `paper_batch_summary.json`, loads each candidate's `manifest.json`, `equity_curve.csv`, `guard_events.csv`, and optional `execution_events.csv`, writes JSON/Markdown/CSV artifacts, and prints a compact summary.

`scripts/run_checks.py` includes the observation pack after paper simulation so local checks keep paper evidence current.

`quant_robot.ops.evidence_refresh` recommends `run_paper_observation.py` after paper-batch refresh and before rebuilding promotion reports.

## Testing

Use unittest:

- `tests/unit/test_paper_observation.py`
- `tests/unit/test_paper_observation_cli.py`
- `tests/unit/test_evidence_refresh.py`
- `tests/unit/test_check_plan.py`

Full verification requires compile checks, artifact generation, and `scripts/run_checks.py --execute`.
