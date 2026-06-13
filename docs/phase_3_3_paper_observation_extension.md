# Phase 3.3 Paper Observation Extension

Phase 3.3 turns local paper simulations into a review-ready observation evidence pack.

It is still research-only. It does not connect to a broker, read accounts, place orders, or approve live trading.

## What It Adds

- Paper observation builder in `quant_robot.ops.paper_observation`.
- CLI artifact generation through `scripts/run_paper_observation.py`.
- Core-check integration after paper simulation.
- Evidence Refresh now recommends paper observation evidence after refreshing paper batches.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_observation.py --paper-batch-summary data\reports\paper_batch_cn_etf_candidate_search\paper_batch_summary.json --output-dir data\reports\paper_observation
```

Output files:

- `paper_observation_pack.json`
- `paper_observation_pack.md`
- `paper_observation_candidates.csv`
- `paper_observation_risk_profiles.csv`
- `paper_observation_trend.csv`

## Interpretation

The pack summarizes:

- completed, skipped, failed, and observed candidates;
- observation start/end dates from each candidate equity curve;
- guard-event counts, trigger events, blocked-buy events, and blocked-buy intent counts;
- execution-block event counts and reasons when `execution_events.csv` exists;
- risk-profile comparison across completed candidates;
- Sharpe, return, drawdown, guard-event, and execution-event trend rows by candidate rank.

## Current Role In The Roadmap

Promotion Review currently treats the top CN ETF candidate as `paper_ready`, but still blocked for manual live review by data quality, provider readiness, duplicate clusters, and manual-review policy. Phase 3.3 makes the paper part more durable: future review packets can discuss how long the candidate was observed, which guard events fired, and whether risk profiles behave consistently.

After rerunning paper batches, rerun:

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_observation.py --paper-batch-summary data\reports\paper_batch_cn_etf_candidate_search\paper_batch_summary.json --output-dir data\reports\paper_observation
python scripts\run_promotion_report.py --config configs\promotion_gate_cn_etf_candidate_search.json
python scripts\run_promotion_ops.py --output-dir data\reports\promotion_ops
python scripts\run_promotion_review.py --output-dir data\reports\promotion_review
python scripts\run_evidence_refresh.py --output-dir data\reports\evidence_refresh
```
