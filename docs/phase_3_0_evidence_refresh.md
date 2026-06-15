# Phase 3.0 Evidence Refresh

Phase 3.0 turns the Phase 2.9 review packet into an ordered local evidence-refresh plan.

It is still pre-API and research-only. It does not connect to a broker, read accounts, place orders, approve live trading, or download market data by itself.

## What It Adds

- Evidence-refresh planner in `quant_robot.ops.evidence_refresh`.
- CLI artifact generation through `scripts/run_evidence_refresh.py`.
- GUI API endpoint at `/api/promotion/evidence-refresh`.
- Promotion Ops page sections for refresh status, refresh tracks, and ordered actions.
- Core-check integration after `promotion_review`.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_promotion_ops.py --output-dir data\reports\promotion_ops
python scripts\run_promotion_review.py --output-dir data\reports\promotion_review
python scripts\run_evidence_refresh.py --output-dir data\reports\evidence_refresh
```

Output files:

- `evidence_refresh_plan.json`
- `evidence_refresh_plan.md`
- `evidence_refresh_actions.csv`

If `data/reports/promotion_review/promotion_review_packet.json` is missing, the refresh CLI rebuilds the review packet first and then writes the refresh plan.

## Refresh Tracks

The plan splits the current blocker set into five tracks:

- `data_quality`: missing dates, duplicate bars, and zero-volume evidence.
- `provider_readiness`: optional packages, tokens, and provider status evidence.
- `paper_observation`: longer local paper observation and promotion-report rebuilds.
- `duplicate_resolution`: duplicate candidate clusters that should count as one canonical edge.
- `manual_review_gate`: final blocker that remains closed until upstream tracks are clean.

Phase 3.1 adds the first concrete data-quality action: `scripts/run_data_quality_audit.py`, which lists exact missing asset/date rows before any CSV refresh.

Each track has a status:

- `clear`: no local action needed for that track.
- `continue`: evidence exists, but more observation is still useful.
- `action_required`: the track needs local refresh work.
- `blocked`: the track must not progress until earlier evidence is clean.

## API Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_gui.py
```

Then request:

```text
http://127.0.0.1:8765/api/promotion/evidence-refresh
```

The endpoint accepts the same path overrides as `/api/promotion/review`:

- `promotion_report`
- `provider_status`
- `quality_report`
- `candidate_id`

## Current Interpretation

For the current CN ETF candidate search, Phase 3.0 produces an `action_required` plan. The top candidate remains `CN_ETF_liquidity_10_top1_cost5_reb5`, but the refresh plan keeps manual live review blocked until data quality, provider readiness, and duplicate-cluster evidence are refreshed.

This is the right next step before any external API boundary: work the evidence, not the broker.
