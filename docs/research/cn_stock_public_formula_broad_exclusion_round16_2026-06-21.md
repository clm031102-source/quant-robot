# CN Stock Public Formula Broad Exclusion Probe Round 16

Date: 2026-06-21

## Purpose

Round 16 tested whether the strongest public formula signals become more useful when translated from concentrated Top50/Top100 stock picks into wider non-bottom baskets.

This is a bottom-exclusion probe, not a new factor-family search. The idea was simple: if the signal mainly identifies losers, broader Top300/Top500/Top1000/Top2000 baskets should reduce single-name capacity pressure and reveal whether excluding the lower-ranked tail improves long-only returns.

## Configuration

Config:

- `configs/experiment_grid_cn_stock_public_formula_broad_exclusion_probe_20260621.json`

Data:

- Authority bars config: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
- Data manifest: `data/reports/cn_stock_data_manifest_adjusted_ratio_clean`
- Clean 2015-2025 CN stock bars with adjusted-ratio jump assets excluded.

Grid:

- Factors:
  - `formula_pv_corr_reversal_20`
  - `formula_volume_contraction_reversal_20`
- TopN: 300, 500, 1000, 2000
- Rebalance interval: 10, 20
- Cost: 10 bps
- Forward horizon: 20
- Regime filter: enabled, lookback 120
- Market impact/capacity: enabled

## Runtime Note

The full grid was 16 cases. The run exceeded the command timeout and produced 12 completed partial rows before stopping. The missing rows are the heaviest remaining broad baskets for `formula_volume_contraction_reversal_20`.

The 12 completed cases already cover:

- all `formula_pv_corr_reversal_20` Top300/500/1000/2000 cases,
- `formula_volume_contraction_reversal_20` Top300/500 cases.

Given the completed evidence, rerunning the remaining heaviest broad cases was not cost-effective for this round.

## Evidence

Partial output:

- `data/reports/experiment_grid_cn_stock_public_formula_broad_exclusion_probe_20260621_clean/partial_leaderboard.jsonl`

Audit output:

- `data/reports/ic_portfolio_gap_audit_public_formula_broad_exclusion_round16_20260621`

Audit summary:

- Cases completed: 12
- Strong RankIC cases: 12
- IC-to-portfolio gap cases: 12
- Exclusion signal cases: 12
- Capacity-limited cases: 1
- Extreme trade cases: 0
- Promotable long-only cases: 0

Best completed rows:

| Case | Total return | Sharpe | Overlap Sharpe | Max DD | Win rate | RankIC | RankIC t | Capacity-limited trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `volume_contraction_top300_reb20` | 0.1077 | 0.0845 | 0.1077 | -0.3310 | 0.4914 | 0.0879 | 5.02 | 1 |
| `volume_contraction_top500_reb20` | 0.1624 | 0.0839 | 0.0955 | -0.3219 | 0.4855 | 0.0879 | 5.02 | 0 |
| `pv_corr_top500_reb20` | 0.1834 | 0.0866 | 0.0893 | -0.3049 | 0.4615 | 0.0707 | 4.58 | 0 |
| `pv_corr_top1000_reb20` | 0.1573 | 0.0708 | 0.0724 | -0.3429 | 0.4520 | 0.0707 | 4.58 | 0 |

## Interpretation

What improved:

- Capacity improved materially. The original Round12/14 formula tests had many capacity-blocked cases; this wider basket probe had only 1 capacity-limited case among 12 completed rows.
- Data remained clean: no extreme-trade flags.
- RankIC stayed statistically significant.

What still failed:

- Every completed case still failed `relative_return_below_threshold`.
- Sharpe and overlap-adjusted Sharpe remain far too low.
- Win rate remains below or near 50%.
- Drawdowns are still around 30%-45%.
- The broad baskets still do not beat the CN benchmark over 2015-2025.

## Decision

Stop testing broader stock TopN variants of this formula family as a standalone long-only strategy.

The useful signal is still:

- ranking / exclusion,
- long-short spread,
- possible breadth or risk-control input.

The useless translation is:

- direct CN stock TopN long-only buying, whether concentrated or broad.

## Next Direction

Round 17 should rotate away from raw CN-stock TopN portfolios and test one of these:

1. Stock-to-ETF/theme breadth bridge.
2. Market/sector beta diagnostic explaining why high IC does not beat benchmark.
3. A pure exclusion/risk overlay applied to an independently profitable buy signal.

The most aligned next step is ETF/theme breadth, because the original project objective is ETF rotation and this stock factor family may be more valuable as ETF risk/breadth evidence than as a direct stock portfolio.

## Current Conclusion

Round 16 produced 0 new factors and 0 promotable factors.

It did produce a decisive process result: broadening the stock basket fixes much of the capacity problem but not the profitability problem. The direction must now move from "stock TopN factor mining" to "stock signal to ETF/theme/risk translation."
