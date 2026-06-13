# Phase 2.8 Promotion Operations

Phase 2.8 turns the Phase 2.7 promotion report into a local operations entry point while keeping the project pre-API and research-only.

It does not connect to brokers, read accounts, place orders, or make live-trading decisions.

## What It Adds

- Promotion operations summary service in `quant_robot.ops.promotion_console`.
- Local GUI API endpoint at `/api/promotion/ops`.
- Live-review blocker aggregation across promotion warnings, provider readiness, and data quality.
- Duplicate-candidate clusters so equivalent paper-ready signals are counted as one canonical candidate.
- Operator next actions such as refreshing data quality, refreshing provider status, extending paper observation, and collapsing duplicate candidates.
- Tushare CN ETF daily provider ingestion path using `fund_daily`, with offline-testable fixtures.
- Paper-simulation execution constraint events for suspended bars, zero-volume bars, limit-up buy blocks, and limit-down sell blocks.

## Promotion Operations API

```powershell
$env:PYTHONPATH='src'
python scripts\run_gui.py
```

Then request:

```text
http://127.0.0.1:8765/api/promotion/ops
```

The API reads the candidate-search promotion report first:

```text
data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json
```

If that report is unavailable, it falls back to:

```text
data/reports/promotion_gate_cn_etf/promotion_report.json
```

Important fields:

- `summary`: counts by promotion state.
- `top_candidate`: the strongest current candidate card.
- `live_review_allowed`: always conservative; false unless a future report contains `manual_live_review` and no blockers.
- `live_review_blockers`: consolidated reasons that stop review progression.
- `duplicate_clusters`: duplicate signal groups keyed by canonical candidate.
- `next_actions`: local operator actions for the next evidence refresh.

## Promotion Operations CLI

The same payload can be generated as local report artifacts:

```powershell
$env:PYTHONPATH='src'
python scripts\run_promotion_ops.py --output-dir data\reports\promotion_ops
```

Output files:

- `promotion_ops.json`
- `promotion_ops_candidates.csv`
- `promotion_ops_actions.csv`

`scripts/run_checks.py --execute` now includes this step after paper simulation. It is followed by the Phase 2.9 review packet step. If no promotion report exists yet, the CLI writes a safe empty operations payload with `promotion_report_missing` instead of crossing any external boundary.

## Tushare CN ETF Ingestion

Tushare now reports CN ETF support in provider status when the optional package and token are present. The adapter routes `CN_ETF` OHLCV requests and daily full-market fetches through `fund_daily`.

Offline fixture ingest:

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source tushare-fixture --market CN_ETF --output-dir data\processed\tushare_etf_fixture
```

Live provider ingest remains optional and token-gated:

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source tushare --market CN_ETF --start-date 2024-01-02 --end-date 2024-01-31 --output-dir data\processed\tushare_etf
```

The output partition uses `market=CN_ETF`, asset IDs such as `CN_ETF_XSHG_510300`, and asset type `etf`.

## Execution Realism

Paper simulation now preserves local execution-block events:

- `suspended`
- `zero_volume`
- `limit_up_buy_blocked`
- `limit_down_sell_blocked`

These events are written to `execution_events.csv` when paper artifacts are saved, and `metrics.execution_block_event_count` records the number of blocked fills. The events are still simulated evidence, not broker feedback.

## Current Interpretation

The project can now distinguish a paper-ready candidate from an operations-ready candidate. A candidate can remain `paper_ready` while still blocked from manual live review because data quality is incomplete, providers are not ready, duplicate signal evidence is present, or execution constraints need more observation.

This keeps the next phase focused on evidence freshness and operational discipline before any broker/API boundary is crossed.
