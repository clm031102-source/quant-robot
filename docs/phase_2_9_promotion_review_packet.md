# Phase 2.9 Promotion Review Packet

Phase 2.9 turns the Phase 2.8 promotion operations console into a durable review packet for the current top candidate.

The packet is still pre-API and research-only. It does not connect to a broker, read accounts, place orders, or approve live trading.

## What It Adds

- Review-packet builder in `quant_robot.ops.review_packet`.
- CLI artifact generation through `scripts/run_promotion_review.py`.
- GUI API endpoint at `/api/promotion/review`.
- Promotion Ops page sections for review status, manual-review gate, checklist, and Markdown packet text.
- Core-check integration after `promotion_ops`.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_promotion_ops.py --output-dir data\reports\promotion_ops
python scripts\run_promotion_review.py --output-dir data\reports\promotion_review
```

Output files:

- `promotion_review_packet.json`
- `promotion_review_packet.md`
- `promotion_review_checklist.csv`

If `data/reports/promotion_ops/promotion_ops.json` is missing, the review CLI rebuilds the promotion operations artifact first and then writes the packet.

## API Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_gui.py
```

Then request:

```text
http://127.0.0.1:8765/api/promotion/review
```

The endpoint accepts the same path overrides as `/api/promotion/ops`:

- `promotion_report`
- `provider_status`
- `quality_report`

It also accepts `candidate_id` when you want a packet for a specific candidate.

## Packet Contents

- `selected_candidate`: current top candidate, or the requested `candidate_id`.
- `review_status`: `blocked`, `paper_observation`, `ready_for_manual_review`, or `missing_candidate`.
- `manual_review_gate`: conservative gate state and blocking reasons.
- `checklist`: research boundary, provider readiness, data quality, walk-forward evidence, paper observation, and duplicate-cluster checks.
- `markdown`: human-readable review packet for copy/paste into reports.
- `next_actions`: carried forward from Promotion Ops.

## Current Interpretation

The project now has a clean handoff from candidate search to operations review:

1. Phase 2.7 classifies candidates.
2. Phase 2.8 summarizes operations blockers and next actions.
3. Phase 2.9 creates an auditable review packet for the selected candidate.
4. Phase 3.0 converts the review blockers into an ordered local evidence-refresh plan.

For the current CN ETF evidence set, the top candidate can be paper-ready while the review packet remains blocked by provider readiness, data quality, or manual-review gate checks. This is the intended conservative behavior before any external API boundary.
