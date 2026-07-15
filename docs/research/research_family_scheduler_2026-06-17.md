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

Current primary allocation:

- `cn_etf_flow_breadth_aggregation`: 0.35, using stock flow only after ETF-level aggregation.
- `cn_etf_fund_structure`: 0.35, subject to source permission and coverage checks.
- `cn_etf_peer_relative_value`: 0.30, restricted to metadata-readiness review before factor implementation.

The peer-relative-value family must first establish point-in-time same-index or tightly defined same-theme mappings. A name-only mapping, factor batch before readiness, portfolio grid before prescreen, or walk-forward before prescreen is prohibited.

No single family should consume more than the configured per-family budget cap.
At least three primary ETF research families must be active before a new factor batch starts.

## Operational Command

Run the scheduler before a factor-mining batch:

```powershell
python scripts\run_research_family_scheduler.py --config configs\research_family_scheduler_cn_etf.json
```

The generated pack is local research output under `data/reports/research_family_scheduler/`.
It is intentionally not a live-trading signal and does not cross the broker boundary.
