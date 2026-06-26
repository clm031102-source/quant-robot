# CN Stock Factor Mining Rounds 4-6 Audit

- Date: 2026-06-21
- Machine: office_desktop
- Task: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Review cadence: required after every 3 rounds
- Scope: CN A-share stock cross-sectional alpha, not ETF rotation

## Executive Decision

Rounds 4-6 produced 3 new daily-basic value/liquidity/tail candidates and 0 promotable factors.

The useful result is methodological: a major adjusted-price data artifact was found, blocked, repaired at read time, and replayed with the same parameters. This prevents future mining from rewarding fake alpha caused by mass adjusted-price discontinuities.

The alpha result is still weak. `value_low_turnover_low_tail_20` is the only component-level research lead, but it is not a standalone tradable factor.

## Candidate Count

| round | family/work | candidates | promotable | research leads | main outcome |
|---|---|---:|---:|---:|---|
| 4 | `daily_basic_value_liquidity_tail` | 3 | 0 | 1 | Positive IC but all rejected; extreme trades exposed data artifact |
| 5 | extreme-trade + manifest audit | 0 | 0 | 0 | Found mass adjusted-ratio jumps on 2023-07-03 and 2025-07-01 |
| 6 | read-time repair + same-parameter replay | 3 replayed | 0 | 1 | Mass jumps cleared; factors still fail relative-return gates |

## Before/After Repair

| factor | pre-repair total return | post-repair total return | post-repair Sharpe | post-repair overlap-adj Sharpe | post-repair max DD | post-repair relative return | decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `value_low_turnover_low_tail_20` | 91.71 | 2.36 | 0.668 | 0.345 | -41.97% | -35.41 | rejected |
| `dividend_value_liquid_low_tail_20` | 62.01 | 0.97 | 0.443 | 0.230 | -50.07% | -36.80 | rejected |
| `value_liquid_low_tail_20` | 58.32 | 1.26 | 0.455 | 0.230 | -50.79% | -36.50 | rejected |

The huge pre-repair returns were not alpha. They were mostly adjusted-price contamination.

## What Worked

- The 3-round audit cadence caught a bad direction before expanding it.
- Extreme-trade diagnostics traced portfolio anomalies back to `adj_close / close` discontinuities.
- The CN data manifest now blocks mass adjusted-ratio jumps as critical.
- The read-time repair cleared mass jump dates without mutating processed data.
- Same-parameter replay showed the real economic strength after removing the largest artifact.

## What Failed

- Daily-basic value/liquidity/tail did not beat the CN benchmark over 2015-2025.
- IC significance did not translate into enough portfolio-level edge.
- Relative return remained deeply negative for all three replayed candidates.
- Two candidates still touched residual single-name adjusted-price anomalies.
- The factor family is too broad-market defensive to be a standalone long-only alpha in this test.

## Direction Change

Stop:

- Do not expand `daily_basic_value_liquidity_tail` by more windows/topN/cost before adding new economic structure.
- Do not promote anything that depends on 2025 single-name adjusted-price anomalies.
- Do not treat IC alone as enough evidence.

Keep:

- Use `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_repaired.json` for CN stock research replays.
- Keep `value_low_turnover_low_tail_20` as a possible component for residualized multi-factor tests.
- Keep the manifest critical gate and extreme-trade diagnostic in every factor family audit.

Next 3-round cycle:

- Round 7: public price-volume/trend-confirmed family, using SuperTrend/ATR trend state plus smart-money-style volume confirmation.
- Round 8: residualized composite family, neutralizing size/liquidity/momentum exposure before ranking.
- Round 9: audit Rounds 7-8, choose whether anything earns walk-forward budget.

Hard gates for the next cycle:

- Use repaired authority bars and reviewed data manifest.
- Add or document single-name anomaly quarantine before any promotion claim.
- Max drawdown must be better than -50%.
- Relative return must be above 0 in the long-cycle fast gate.
- Extreme trade flag must be false or fully isolated.
- Overlap-adjusted Sharpe should be above 0.5 before walk-forward.
- Tail IC must not be significantly negative.
- Capacity-limited trades must be zero or economically immaterial.
