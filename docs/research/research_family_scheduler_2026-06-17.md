# Research Family Scheduler

This note turns factor-mining direction changes into a formal scheduling rule.
The failure mode to avoid is staying too long inside one rejected research family and spending new compute on parameter rescue instead of new hypotheses.

## Current Decision

The direct `CN` stock moneyflow selection family is downgraded to `auxiliary_only`.
It had a reasonable original thesis: large-order behavior, retail sell pressure, liquidity crowding, and short-term supply/demand imbalance.
The latest evidence repeatedly hit the same blockers: capacity, cost sensitivity, out-of-sample relative return, and tail-IC instability.

Allowed use after downgrade:

- Aggregate stock moneyflow into ETF-level market breadth.
- Aggregate theme or industry flow diffusion for ETF rotation.
- Use broad risk-appetite proxies as auxiliary ETF features.

Forbidden use after downgrade:

- Direct `CN` stock selection as a primary research line.
- More top-N widening to rescue the same family.
- More liquidity-gate, amount-floor, single-regime, or holding-period rescues for the same direct moneyflow family.

The `cn_etf_price_rotation` and `cn_etf_liquidity_capacity` families are now stop-lossed with zero budget. Their negative prescreens prohibit sign, window, threshold, portfolio-grid, and walk-forward rescue.

The `cn_etf_volatility_regime` final market-residual prescreen produced zero research leads. The family is now stop-lossed with zero budget. Residual-volatility retry, downside-beta retry, residual-skew sign flip, window or threshold rescue, portfolio grids, and walk-forward are prohibited.

## ETF Rotation Hypothesis Portfolio

Current state, reconciled on 2026-09-21 against `configs/research_family_scheduler_cn_etf.json`:

- Seven CN ETF families are explicitly `stop_lossed`: NAV premium, price rotation, liquidity capacity, volatility regime, fund structure, dynamic co-movement peer dislocation, and margin positioning. Every budget is zero.
- Flow breadth aggregation, peer relative value, and option sentiment remain exploratory at zero budget with unresolved source or breadth requirements.
- CN stock moneyflow remains `auxiliary_only` at zero primary budget.
- Active primary families: zero. Allocated primary budget: zero. Unallocated budget: 1.0.
- The scheduler reports eight triggered stop losses because it also counts the auxiliary CN stock family's historical stop-loss trigger. This is not eight closed ETF families.

The latest delayed-NAV execution was invalidated, not accepted or statistically rejected. Its authorization was consumed and cannot be reused. The governing decision permits only `family_rotation_review_only` for `factor_review`; factor batches, portfolio grids, walk-forward, promotion, paper signals, and final holdout access remain disabled.

Historical PCF or a historical official ETF-to-index bridge must pass a separate point-in-time source audit before a new independent hypothesis can be preregistered. Current names and metadata cannot substitute for historical availability.

No single family should consume more than the configured per-family budget cap.
The ordinary scheduler requires at least three active primary families. Restricted source review, preregistration, and single-prescreen modes are separate explicit gates; they do not restore an unrestricted batch allocation.

## Operational Command

Run the scheduler before a factor-mining batch:

```powershell
python scripts\run_research_family_scheduler.py --config configs\research_family_scheduler_cn_etf.json
```

The generated pack is local research output under `data/reports/research_family_scheduler/`.
It is intentionally not a live-trading signal and does not cross the broker boundary.
