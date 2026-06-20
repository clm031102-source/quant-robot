# CN Stock Factor Mining Rounds 11-13 Audit

Date: 2026-06-21

## Scope

This audit covers the post-Round-10 work cycle:

- Round 11: daily-basic residual composite factors.
- Data-quality repair: clean authority bars with individual adjusted-ratio jump assets excluded.
- Round 12: public formula price-volume factors.
- Round 13: evidence review and direction adjustment.

## What Improved

The work moved in the right direction compared with the earlier moneyflow-only and trend-volume batches:

- The factor families are now grounded in public, explainable factor templates instead of blind moneyflow mining.
- The data pipeline now has a stricter clean authority-bars option:
  - `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
  - adjusted-ratio jump rows/assets reduced to 0.
  - recurring 600777.SH contamination was isolated.
- New factor sources are reusable and registered in pipeline, experiment runner, and project audit:
  - `daily_basic_residual_composite`
  - `public_formula_price_volume`
- The strongest new signals have real IC/RankIC evidence on the clean 2015-2025 sample.

## Factor Count

New factor names added in this cycle:

- Round 11: 3 residual daily-basic composite factors.
- Round 12: 3 public formula price-volume factors.

Total new registered factors in this cycle: 6.

Promotable factors: 0.

Research leads:

- `formula_pv_corr_reversal_20`
- `formula_volume_contraction_reversal_20`
- `resid_value_low_turnover_quality_20`
- `resid_value_reversal_low_tail_20`

## Why They Still Are Not Profitable

The main failure is not absence of cross-sectional signal. It is the break between rank signal and long-only deployable portfolio return.

Evidence:

- Round 12 formula factors have very strong RankIC:
  - `formula_pv_corr_reversal_20`: RankIC about 0.076, RankIC t-stat 10.88.
  - `formula_volume_contraction_reversal_20`: RankIC about 0.080, RankIC t-stat 10.25.
- Long-short and quantile-spread evidence is positive.
- But naive long-only TopN portfolios have weak or negative absolute returns and all fail relative-return gates.

Interpretation:

- Much of the edge is in identifying losers or relative ranks, not in directly buying a basket that beats the broad CN stock benchmark.
- Market beta and benchmark trend dominate long-only returns over 2015-2025.
- Some high-IC formula variants hit capacity limits.
- TopN ranking ignores sector/theme/beta concentration and does not translate IC into portfolio construction.

## Stop-Loss Decisions

Do not continue these directions as standalone TopN long-only sweeps:

- More moneyflow-only factors.
- More direct trend-volume or anti-trend-volume variants.
- More public formula variants evaluated only as naive TopN long-only baskets.
- More parameter sweeps before fixing IC-to-portfolio translation.

Keep, but demote:

- `resid_value_quality_low_vol_20`: useful as a risk-control component, not alpha.
- `formula_range_contraction_breakout_20`: weak standalone and poor portfolio evidence.

Keep as research leads:

- `formula_pv_corr_reversal_20`: strongest public ranking/exclusion signal.
- `formula_volume_contraction_reversal_20`: strongest long-short spread, but capacity/drawdown issues.
- `resid_value_low_turnover_quality_20`: cleaner daily-basic composite lead.
- `resid_value_reversal_low_tail_20`: secondary residual composite lead.

## Direction Change

Next work should not be "invent more formulas." The next useful direction is portfolio translation:

1. Build a stock-factor-to-ETF/theme breadth bridge, where high-IC stock signals become ETF rotation evidence.
2. Build a bottom-quantile exclusion overlay for long-only portfolios, because the strongest signal may be "avoid losers."
3. Add beta/sector/size exposure diagnostics to explain why high IC fails as long-only return.
4. Test market-regime timing as a separate overlay, not as a hidden parameter patch.

## Governance Check

The new goal requires review every 3 work rounds and GitHub sync every 10 rounds.

- Review gate: satisfied for Rounds 11-13.
- Next review gate: after Rounds 14-16.
- Last GitHub sync: Round 10.
- Next GitHub sync target: Round 20, unless the user explicitly requests an earlier sync.

## Current Conclusion

This cycle produced no tradable factor, but it produced useful evidence and a better process:

- The data is cleaner.
- The blind moneyflow lock-in problem is fixed.
- Public formula factors found strong cross-sectional ranking signal.
- The project now knows the next bottleneck: portfolio construction and translation, not raw factor discovery.
