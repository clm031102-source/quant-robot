# Phase 2.9 Promotion Review Packet Design

## Purpose

Phase 2.9 creates an auditable candidate review packet from the Phase 2.8 Promotion Ops console. The goal is to make the strongest current candidate easy to inspect, archive, and hand off without crossing any broker, account, or live-trading boundary.

## Scope

The feature stays local and read-only. It consumes Promotion Ops output, selects the top candidate by default, and emits JSON, Markdown, and CSV checklist artifacts. It also exposes the packet through the local GUI API and Promotion Ops page.

Out of scope:

- Broker connectivity.
- Account reads.
- Order placement.
- Live-trading approval.
- External data download.

## Architecture

`quant_robot.ops.review_packet` is the single service boundary. It accepts a Promotion Ops console dictionary and returns a packet with:

- selected candidate evidence;
- manual-review gate state;
- checklist rows;
- duplicate-cluster evidence;
- next actions;
- rendered Markdown.

`scripts/run_promotion_review.py` handles filesystem concerns. The GUI service calls the same builder used by the CLI, so the browser, API, and artifacts stay aligned.

## Data Flow

1. Promotion gate writes `promotion_report.json`.
2. Promotion Ops builds `promotion_ops.json`.
3. Promotion Review reads the ops payload, or rebuilds it when missing.
4. Review Packet writes:
   - `promotion_review_packet.json`
   - `promotion_review_packet.md`
   - `promotion_review_checklist.csv`
5. GUI renders review status, checklist, and Markdown from `/api/promotion/review`.

## Checks

Checklist rows are intentionally conservative:

- `research_boundary`: must preserve the research-only safety text.
- `provider_readiness`: blocks unless providers are explicitly ready.
- `data_quality`: blocks on missing quality report, missing dates, duplicate bars, or zero-volume rows.
- `walk_forward_evidence`: warns if candidate test Sharpe or trade count evidence is missing.
- `paper_observation`: warns unless paper evidence matched the candidate.
- `duplicate_cluster`: warns when the selected candidate is canonical for duplicates and blocks when it is itself a duplicate.

## Testing

Use unittest with a red-green cycle:

- `tests/unit/test_promotion_review_packet.py`
- `tests/unit/test_promotion_review_cli.py`
- `tests/unit/test_check_plan.py`
- `tests/unit/test_gui.py`

Full verification also requires Python compile checks, JS syntax checks, `run_checks.py --execute`, and a browser snapshot of the Promotion Ops page.
