# CN Stock Factor Mining Work Report - Rounds 71-78 - 2026-06-21

## Executive Summary

Scope stayed on CN A-share stock cross-sectional factors, not ETF rotation. The work moved from a failed defensive risk-filter family into a public RSRS family, and added stricter translation-layer audits so positive IC is no longer mistaken for tradable alpha.

Current result:

- Promotable profitable factors: 0.
- Paper-ready factors: 0.
- Current research lead: 1, `rsrs_reversal_18_60` as a bottom-exclusion / risk-filter candidate.
- Newly registered public RSRS factors: 4.
- Unique factor names evaluated in Rounds 71-78: 7.
- Parameter/case rows directly reviewed in this block: at least 37, excluding date-level audit rows.

The most important conclusion is not that the project found a ready-to-trade factor. It did not. The useful result is that Round78 found a statistically strong translation lead and the process now blocks the old pattern of blindly expanding parameters after a weak long-only result.

## Direction Of Work

The work direction changed in three steps:

1. Public risk-filter bridge family:
   tested whether weak-tail removal could become a tradable long-only or hedged spread strategy.
2. Family hibernation:
   after static/dynamic overlays and beta-hedged spreads failed, the family was stopped instead of over-tuned.
3. Public RSRS family:
   tested a known public A-share technical method and discovered that the useful side is likely bottom exclusion, not direct TopN buying.

## Round Results

| Round | Direction | Main Result | Decision |
|---:|---|---|---|
| 71 | Static cash overlay | Best `risk_filter_bridge_anti_obv_weighted_20`: total 18.89%, relative 19.62%, Sharpe 0.092, overlap Sharpe 0.069, max DD -42.77%, positive relative folds 10/11, capacity clean | rejected as alpha; risk-filter component only |
| 72 | Dynamic cash overlay | Best 120-day overlay risk-off 0.2: total 11.39%, relative 13.17%, overlap Sharpe 0.0586, max DD -26.09%, positive relative folds 10/11 | rejected; drawdown improved but return stream weak |
| 73 | Benchmark beta exposure | Residual alpha t-stat 4.39-5.42 and residual Sharpe 0.62-0.76, but R2 0.992-0.994 | research lead with beta only |
| 74 | Fixed 1.0 beta-hedged spread | Cost-sign bug found and fixed; corrected best spread total -12.91%, overlap Sharpe -0.516 | rejected |
| 75 | Cost/impact stress | Best stressed spread total -53.74%, overlap Sharpe -1.701 | hibernate risk-filter bridge |
| 76 | Public RSRS registration | Registered `rsrs_slope_18`, `rsrs_zscore_18_60`, `rsrs_right_skew_18_60`, `rsrs_reversal_18_60` | rotate to RSRS |
| 77 | RSRS long-cycle grid | 8/8 cases completed. Best direct result: `rsrs_reversal_18_60` top100 total 72.07%, Sharpe 0.272, overlap Sharpe 0.191, RankIC 0.0214 t=4.77; rejected | 1 research lead only |
| 78 | RSRS translation audit | Neutral RankIC 0.0253 t=24.00; industry-neutral top50 total 80.75%, Sharpe 0.352, overlap Sharpe 0.241; bottom-exclusion overlay t=5.39, positive rate 66.28% | no promotion; continue only as costed bottom-exclusion |

## Bright Data Points

These are the numbers worth noticing, with the caveat that none is promotion evidence by itself.

### 1. Round78 industry-neutral IC was strong

`rsrs_reversal_18_60`:

- Overall RankIC: 0.0214, t=15.97.
- Industry-neutral RankIC: 0.0253, t=24.00.
- Industry-neutral retention ratio: 1.18.

This says the signal survives industry neutralization and is not just industry exposure.

### 2. Round78 bottom-exclusion shape was the best practical lead

`rsrs_reversal_18_60` bottom-exclusion overlay:

- Mean full-universe return: 0.9175%.
- Mean kept-universe return: 1.0210%.
- Mean bottom-quantile return: 0.5030%.
- Mean overlay excess: 0.1035%.
- Overlay t-stat: 5.39.
- Positive overlay rate: 66.28%.
- Kept compounded: 362.69%.
- Full compounded: 257.62%.
- Bottom compounded: 24.21%.

This points to a risk-filter / avoid-bottom use case.

### 3. Industry-neutral TopN improved but still failed

Top50 industry-neutral RSRS reversal:

- Total return: 80.75%.
- Annual return: 2.61%.
- Sharpe: 0.352.
- Overlap-adjusted Sharpe: 0.241.
- Win rate: 50.09%.
- Max drawdown: -40.43%.

This improved over raw top50, but still failed because relative return was deeply negative and capacity-limited trades remained.

### 4. Risk-filter bridge had real residual signal but no executable translation

Round73:

- Residual alpha t-stat: 4.39-5.42.
- Residual Sharpe: 0.62-0.76.

But the same return stream was more than 99% explained by broad benchmark beta, and the corrected spread translation failed. That is useful because it prevents wasting more compute on that family.

### 5. The process caught a serious backtest bug

Round74 found a cost-sign error in the beta-hedged spread implementation. The incorrect read looked positive; the corrected logic made all spreads negative. This was a high-value engineering result because it prevents false profitability claims.

Correct short-leg logic:

`selected_net + (-benchmark_gross - benchmark_cost)`

## Engineering Outputs

Reusable tools added in this work block:

- `src/quant_robot/ops/dynamic_cash_overlay_backtest.py`
- `scripts/run_dynamic_cash_overlay_backtest.py`
- `src/quant_robot/ops/benchmark_beta_exposure_audit.py`
- `scripts/run_benchmark_beta_exposure_audit.py`
- `src/quant_robot/ops/beta_hedged_spread_audit.py`
- `scripts/run_beta_hedged_spread_audit.py`
- `src/quant_robot/factors/public_rsrs.py`
- `configs/experiment_grid_cn_stock_public_rsrs_round76_20260621.json`
- `configs/experiment_grid_cn_stock_public_rsrs_reversal_translation_round78_20260621.json`

Reusable process controls added or reinforced:

- every 3 rounds: evidence review, reject reason histogram, direction adjustment;
- every 10 rounds: package results and safe-sync after validation;
- no promotion from IC alone;
- no more raw public formula TopN sweeps after strong IC / weak portfolio mismatch;
- mandatory translation layer: industry-neutral IC, IC-to-portfolio gap, bottom-exclusion overlay, and costed walk-forward before promotion.

## Why Nothing Is Promotable Yet

The project has not found a live-usable factor in this block because every candidate still fails at least one hard gate:

- overlap-adjusted Sharpe too low;
- drawdown too high;
- benchmark-relative return too weak;
- capacity-limited trades present;
- profitable-looking residual signal failing after correct hedge cost;
- diagnostic overlay not yet converted into costed walk-forward portfolio.

This is exactly why the promotion gate is useful. A weaker process would have promoted Round73 residual alpha or Round78 IC. This process blocks both.

## Current Best Candidate

The only candidate worth continuing now:

`rsrs_reversal_18_60` as a bottom-exclusion / risk-filter factor.

Parameters:

- RSRS slope window: 18.
- RSRS z-score window: 60.
- Direction: negative / reversal of right-skew RSRS.
- Horizon: 20.
- Execution lag: 1.
- Rebalance interval: 10.
- Bottom quantile: 20%.
- Next construction: exclude bottom quantile, not direct TopN long-only promotion.

## Next Plan

Round79 should run a frozen-parameter costed walk-forward bottom-exclusion portfolio:

- use only `rsrs_reversal_18_60`;
- do not expand windows;
- include 10 bps cost, 20 bps impact, capacity gate, turnover, drawdown, overlap-adjusted Sharpe, and fold stability;
- repair or flag industry metadata coverage before any promotion claim;
- if the costed exclusion portfolio fails, hibernate RSRS and rotate to the next public family.
