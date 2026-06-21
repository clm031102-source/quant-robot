# CN Stock Three-Round Review - Rounds 67-69 - 2026-06-21

## Scope

This review covers the governance checkpoint after Rounds 67, 68, and 69.

The block stayed on long-cycle CN A-share authority data from 2015-01-05 through 2025-12-31. It used execution lag, costs where portfolio tests were involved, capacity checks, overlap-aware statistics, and diagnostic gates before any promotion claim.

## Round Summary

| Round | Direction | Candidates | Result | Decision |
|---|---|---:|---|---|
| 67 | Daily-basic residual costed bottom-exclusion portfolio | 2 | Relative return improved, but Sharpe stayed near 0.08-0.09 and max drawdown stayed around -64% | research lead only, line hibernated |
| 68 | Standalone anti-OBV regime focus | 1 | Best total return 3.43%, overlap Sharpe 0.095, relative return about -2370% | rejected, stop standalone anti-OBV |
| 69 | Public risk-filter industry-breadth bridge | 3 | Positive industry RankIC, but positive excess rate only 52%-53%; 0 bridge candidates | ranking-only diagnostics |

Unique factor names evaluated in this block: 6.

Promotable profitable factors: 0.

Paper-ready factors: 0.

Useful outputs:

- A confirmed rejection of daily-basic residual bottom-exclusion as an investable portfolio.
- A confirmed rejection of standalone anti-OBV regime focus.
- A new reusable industry-breadth bridge audit tool.
- Evidence that public risk-filter bridge factors rank industries weakly but do not yet produce a robust industry/ETF rotation edge.

## Main Finding

The project is no longer failing because it has no signal. It is failing because the signals are not yet being converted into controlled portfolio return.

Repeated pattern:

- IC and bottom-tail diagnostics are often real.
- The bottom bucket is much worse than the top bucket is good.
- Broad exclusion or industry ranking improves relative return, but absolute Sharpe and drawdown remain poor.
- Market beta, drawdown regime, and cash allocation dominate the result.

## Stop-Loss Decisions

Do not continue:

- daily-basic residual costed exclusion as a standalone line;
- anti-OBV or public trend-volume single-factor parameter expansion;
- industry-breadth bridge as a standalone promotion candidate;
- more raw TopN stock sweeps before solving portfolio risk.

Keep only as components:

- `risk_filter_bridge_agreement_20`
- `risk_filter_bridge_equal_20`
- `risk_filter_bridge_anti_obv_weighted_20`
- `resid_value_low_turnover_quality_20`
- `resid_value_reversal_low_tail_20`

## Process Adjustment

The next useful work is not another factor family. It is a portfolio-construction gate:

1. Use existing research leads only.
2. Add market/cash regime overlay tests with unchanged factor parameters.
3. Require drawdown reduction, not only relative return.
4. Require positive excess rate and overlap-adjusted Sharpe improvement across rebalance schedules.
5. If cash/regime overlay fails, rotate away from stock TopN mining toward direct ETF broad-universe work or data/portfolio infrastructure.

## Next Direction

Round70 is the ten-round governance boundary and should package lightweight results for GitHub safe-sync.

After Round70 sync, the next mining batch should be:

`market_regime_cash_overlay_for_risk_filter_research_leads_batch`

Pre-registered thesis:

The current signals are better at avoiding bad stocks/industries than selecting high-return stocks. A market/cash overlay may convert them from weak relative diagnostics into lower-drawdown absolute-return strategies. If it cannot, the project should stop spending compute on these stock-factor families.
