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

## ETF Rotation Hypothesis Portfolio

Every material mining round for this project should allocate budget across multiple `CN_ETF` hypothesis families:

- `cn_etf_price_rotation`: relative momentum, skip-window momentum, reversal, and multi-horizon ETF rotation.
- `cn_etf_liquidity_capacity`: liquidity, turnover stability, capacity, and low-turnover ETF factors.
- `cn_etf_volatility_regime`: low volatility, downside risk, drawdown control, and regime-gated ETF rotation.
- `cn_etf_flow_breadth_aggregation`: stock-flow breadth and theme-flow aggregation as ETF-level auxiliary features.
- `cn_etf_fund_structure`: fund share, NAV, scale, and demand-pressure proxies where Tushare coverage permits.

No single family should consume more than the configured per-family budget cap.
At least three primary ETF research families must be active before a new factor batch starts.

## Operational Command

Run the scheduler before a factor-mining batch:

```powershell
python scripts\run_research_family_scheduler.py --config configs\research_family_scheduler_cn_etf.json
```

The generated pack is local research output under `data/reports/research_family_scheduler/`.
It is intentionally not a live-trading signal and does not cross the broker boundary.
