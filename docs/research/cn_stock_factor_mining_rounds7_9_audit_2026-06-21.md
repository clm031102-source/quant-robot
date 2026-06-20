# CN Stock Factor Mining Rounds 7-9 Audit

- Date: 2026-06-21
- Machine: office_desktop
- Task: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Review cadence: required after every 3 rounds
- Scope: CN A-share stock cross-sectional alpha, not ETF rotation

## Executive Decision

Rounds 7-9 produced 6 new trend-volume factor names and 12 focused portfolio variants. Promotable factors: 0.

The useful conclusion is directional: public trend-volume continuation is strongly wrong-way in this CN stock universe. The inverse side has real positive IC, but it is too weak as a standalone long-only portfolio signal.

## Candidate Count

| round | family/work | candidates or cases | promotable | research leads | main outcome |
|---|---|---:|---:|---:|---|
| 7 | public trend-volume continuation | 3 factors | 0 | 0 | Strong negative IC, severe drawdown |
| 8 | inverse public trend-volume | 3 factors | 0 | 1 | IC flips positive; `anti_obv` has weak positive return |
| 9 | `anti_obv` topN/rebalance/regime focus | 12 cases | 0 | 0 | Risk improves, return remains too small |

## Key Evidence

Continuation failed:

- `obv_breakout_low_tail_20`: mean IC -0.0341, total return -0.67, max DD -91.09%.
- `smart_money_trend_20`: mean IC -0.0491, total return -0.72, max DD -92.45%.
- `supertrend_volume_confirmed_10_3_20`: mean IC -0.0450, total return -0.78, max DD -93.47%.

Inversion helped but did not pass:

- `anti_obv_breakout_low_tail_20`: mean IC 0.0341, total return 0.50, Sharpe 0.238, overlap-adj Sharpe 0.135, max DD -57.34%.
- Focused best row `top50/reb10/regime120`: total return 0.086, Sharpe 0.113, overlap-adj Sharpe 0.121, max DD -37.99%, no capacity-limited trades, no extreme flag.

The best risk-managed variant is cleaner but not profitable enough. It fails only relative return, which is the right failure: the signal is not competitive with the available benchmark opportunity.

## What Worked

- The repaired data baseline prevented mass adjusted-price artifacts from dominating the result.
- The 3-round review forced a sign correction after seeing significant negative IC.
- The focused Round 9 grid avoided unbounded parameter search.
- Regime filtering and slower rebalance improved drawdown and capacity.

## What Failed

- Public trend-following/volume-confirmation is not a standalone long-only alpha here.
- The inverse signal is too weak after costs and broad-market comparison.
- IC remains useful diagnostically, but still overstates portfolio value.
- TopN and regime construction cannot rescue a thin edge.

## Direction Adjustment

Stop:

- Do not expand standalone public trend-volume continuation.
- Do not spend walk-forward budget on `anti_obv_breakout_low_tail_20` as a standalone factor.
- Do not add more topN/rebalance permutations for this family unless it is inside a broader model.

Keep:

- Keep `public_trend_volume` as a reusable feature source.
- Keep the inverse trend-volume fields as potential overextension/risk features.
- Keep `top50/reb10/regime120` only as a diagnostic benchmark, not a promotion candidate.

Next cycle:

- Move to residualized multi-factor research: value/liquidity/quality/low-vol plus overextension features, neutralized against size/liquidity/momentum exposure.
- Add a bridge report that maps CN stock alpha findings back to the real target: ETF rotation signals should use stock factors only if they aggregate into sector/theme/ETF-level breadth or risk-on/risk-off evidence.
- Keep the hard gates: repaired manifest, no extreme flag, no capacity-limited trades, relative return above zero, overlap-adjusted Sharpe above 0.5, and max drawdown better than -50%.
