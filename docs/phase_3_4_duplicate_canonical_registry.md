# Phase 3.4 Duplicate Canonical Registry

Phase 3.4 turns duplicate candidate suppression into a stable local registry.

It is still research-only. It does not connect to a broker, read accounts, place orders, or approve live trading.

## What It Adds

- Duplicate registry builder in `quant_robot.ops.duplicate_registry`.
- CLI artifact generation through `scripts/run_duplicate_registry.py`.
- Core-check integration after Promotion Ops.
- Evidence Refresh now recommends building a duplicate canonical registry during duplicate-resolution work.
- Promotion Ops and Promotion Review Packet now include duplicate registry summary fields.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_duplicate_registry.py --promotion-report data\reports\promotion_gate_cn_etf_candidate_search\promotion_report.json --output-dir data\reports\duplicate_registry
```

Output files:

- `duplicate_canonical_registry.json`
- `duplicate_canonical_registry.md`
- `canonical_candidates.csv`
- `duplicate_members.csv`

## Interpretation

The registry has two main tables:

- `canonical_registry`: every non-duplicate candidate, plus duplicate counts and member IDs.
- `duplicate_members`: every suppressed duplicate, its canonical candidate, similarity score, and suppression reason.

The suppression reason prefers explicit duplicate blockers such as `duplicate_signal_candidate`, then duplicate warnings such as `duplicate_of:<case_id>`.

## Current Role In The Roadmap

Promotion Gate already blocks duplicate signal candidates. Phase 3.4 makes that decision durable by writing a stable registry that Review Packet and GUI-facing Promotion Ops can summarize. This prevents equivalent liquidity-window variants from looking like independent edges during manual review.
