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

The `cn_etf_volatility_regime` review closed raw volatility, low volatility, downside volatility, drawdown, recovery, compression, hard-regime, and state-adaptive retries. It retains 0.35 only for one final three-candidate market-residual prescreen. A zero-lead result closes the family immediately.

## ETF Rotation Hypothesis Portfolio

Current primary allocation:

- `cn_etf_volatility_regime`: 0.35, limited to `etf_idio_vol_low_60`, `etf_downside_beta_low_120`, and `etf_positive_residual_skew_60`.
- `cn_etf_flow_breadth_aggregation`: 0.35, using stock flow only after ETF-level aggregation.
- `cn_etf_fund_structure`: 0.30, subject to source permission and coverage checks.

Frozen zero-lead transition for the residual-volatility batch:

- Stop-loss `cn_etf_volatility_regime` at 0.
- Keep flow breadth at 0.35.
- Raise fund structure to 0.35.
- Activate `cn_etf_peer_relative_value` at 0.30 after a metadata-readiness review and separate preregistration.

No single family should consume more than the configured per-family budget cap.
At least three primary ETF research families must be active before a new factor batch starts.

## Operational Command

Run the scheduler before a factor-mining batch:

```powershell
python scripts\run_research_family_scheduler.py --config configs\research_family_scheduler_cn_etf.json
```

The generated pack is local research output under `data/reports/research_family_scheduler/`.
It is intentionally not a live-trading signal and does not cross the broker boundary.
