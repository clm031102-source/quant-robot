# Phase 4.0 Pre-API Readiness Board

Phase 4.0 consolidates local evidence into one pre-API readiness board.

It remains research-only. It does not connect to providers, brokers, accounts, order systems, or live trading.

## What It Adds

- Readiness board builder in `quant_robot.ops.pre_api_readiness_board`.
- CLI artifact generation through `scripts/run_pre_api_readiness_board.py`.
- Core-check integration after Evidence Refresh.
- One consolidated blocker register and next-local-action list across Phase 3 evidence packs.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

Output files:

- `pre_api_readiness_board.json`
- `pre_api_readiness_board.md`
- `pre_api_readiness_items.csv`
- `pre_api_blockers.csv`
- `pre_api_next_actions.csv`

## Interpretation

The board summarizes:

- data-quality readiness;
- data-gap resolution ledger state;
- provider and Parquet readiness;
- paper-observation evidence;
- duplicate canonical registry state;
- manual-review gate state;
- evidence-refresh action state;
- live-boundary safety state.

The board status is:

- `blocked` when any hard blocker remains;
- `needs_review` when no hard blocker remains but warning tracks still need review;
- `ready_for_api_boundary_planning` only when local evidence is clean and the live boundary is still disabled.

## Current Local State

The current board remains blocked. It points to three main local blocker families:

- CN ETF missing-date evidence still has unresolved gaps.
- The data-gap resolution ledger still marks those gaps as blocking until local evidence is recorded.
- Provider readiness is not clean because optional dependencies/tokens and Parquet support are missing.
- Manual live review remains disabled by design.

That is the intended Phase 4.0 outcome: one local command now tells the project what remains before future API-boundary planning can even be discussed.
