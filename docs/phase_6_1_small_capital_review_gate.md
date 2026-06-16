# Phase 6.1 Small Capital Review Gate

## What Changed

Phase 6.1 adds a local-only gate for preparing a small-capital manual review packet.

It consumes the existing evidence chain:

1. Promotion review packet
2. Manual review rehearsal
3. Paper observation pack
4. Pre-API readiness board
5. Observation sufficiency pack
6. Market regime coverage pack
7. Small-capital risk policy

The gate writes:

- `data/reports/small_capital_review_gate/small_capital_review_gate.json`
- `data/reports/small_capital_review_gate/small_capital_review_gate.md`
- `data/reports/small_capital_review_gate/small_capital_review_requirements.csv`

## Decision Rule

The gate returns `ready_for_manual_small_capital_review` only when:

- The selected candidate is promoted to `manual_live_review`.
- Manual review rehearsal is ready and has no blockers.
- Pre-API readiness is clear and does not cross the live boundary.
- Paper observation has enough completed and observed candidates.
- Paper fills, observation days, drawdown, guard events, and execution events pass policy.
- Observation sufficiency is clear.
- Market regime coverage clears at least the configured number of regimes.
- The execution boundary remains disabled for broker connection, account reads, and order placement.

Even when the gate is ready:

- `live_boundary_allowed` remains `false`.
- `executable` remains `false`.
- `live_order_allowed` remains `false`.
- A manual approval packet is produced, but it is not an order ticket.

## Default Policy

The default policy is in `configs/small_capital_review_policy.json`:

- `max_initial_capital`: `10000.0`
- `max_single_order_notional`: `1000.0`
- `max_daily_loss`: `200.0`
- `max_paper_drawdown`: `0.08`
- `min_paper_fills`: `30`
- `min_observation_days`: `20`
- `max_guard_events`: `0`
- `max_execution_events`: `0`
- `min_market_regimes`: `2`

## Command

Build market-regime coverage from a research `regime_curve.csv`:

```powershell
$env:PYTHONPATH='src'
python scripts\run_market_regime_coverage.py --regime-curve data\reports\research_pipeline\regime_curve.csv --min-regimes 2 --min-rows-per-regime 5
```

Then build the small-capital review gate:

```powershell
$env:PYTHONPATH='src'
python scripts\run_small_capital_review_gate.py --reviewer operator
```

Custom policy:

```powershell
$env:PYTHONPATH='src'
python scripts\run_small_capital_review_gate.py --policy configs\small_capital_review_policy.json --reviewer operator
```

## Boundary

This stage does not connect to a broker, read account data, place orders, approve live trading, or relax the research evidence gates.

It only answers one question: whether the local evidence package is clean enough for a human to consider a tightly capped small-capital pilot.
