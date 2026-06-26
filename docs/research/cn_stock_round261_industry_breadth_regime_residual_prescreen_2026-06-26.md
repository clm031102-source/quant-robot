# CN Stock Round261 Industry Breadth-Regime Residual Prescreen

Date: 2026-06-26

Machine: office_desktop

Branch: codex/factor-validation-cn-stock-long-cycle-20260618

Stage: residual prescreen, research-to-review only

## Direction

Round261 tested the industry breadth and internal dispersion regime translation family. The aim was to avoid another blind single-indicator line by using a market-structure hypothesis: broadening or overheating inside an industry may translate into stock-level residual rebound, breakout, or avoidance signals.

This was deliberately not the old industry leader-lag family. It used industry participation breadth, industry internal dispersion, and stock returns relative to industry state, then forced the candidates through industry neutralization and size/liquidity/volatility residualization.

## Candidates

Six pre-registered factors were evaluated on 5-day and 20-day horizons:

- industry_breadth_repair_laggard_rebound_20
- industry_breadth_volume_confirmed_repair_20
- industry_dispersion_compression_breakout_20
- industry_internal_dispersion_laggard_reversal_20
- industry_breadth_overheat_runup_avoidance_10
- industry_breadth_turning_point_resilience_20

The candidate plan gate passed with all eight control areas present. Portfolio grids, promotion, final holdout use, and live trading remained blocked.

## Full-Sample Evidence

The full core run covered 2015-01-01 to 2025-12-31 with the long-cycle CN stock bar roots.

| Metric | Value |
|---|---:|
| Candidates | 6 |
| Horizon tests | 12 |
| Asset count | 5,707 |
| Bar rows | 10,785,537 |
| Factor rows | 58,741,047 |
| Industry-neutral rows | 58,740,873 |
| Residual rows | 58,630,164 |
| Label rows | 21,442,336 |
| Residual research leads | 0 |
| Portfolio preflight candidates | 0 |
| Promotion allowed candidates | 0 |

The 2024Q1 smoke run also had zero residual leads, so there was no short-window survivor to audit. The long-cycle run confirmed the family is not strong enough as a direct stock alpha line.

## Best Diagnostics

| Factor | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | t | Pos IC | Year Fail | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| industry_breadth_overheat_runup_avoidance_10 | 20 | 0.0316 | 0.0582 | 0.0127 | 0.149 | 7.605 | 0.5496 | 5 | reject |
| industry_breadth_overheat_runup_avoidance_10 | 5 | 0.0218 | 0.0512 | 0.0113 | 0.130 | 6.653 | 0.5299 | 5 | reject |
| industry_breadth_repair_laggard_rebound_20 | 20 | 0.0405 | 0.0636 | 0.0092 | 0.100 | 5.155 | 0.5283 | 6 | reject |
| industry_internal_dispersion_laggard_reversal_20 | 20 | -0.0167 | 0.0631 | 0.0091 | 0.100 | 5.124 | 0.5291 | 6 | reject |
| industry_dispersion_compression_breakout_20 | 20 | 0.0272 | -0.0264 | -0.0204 | -0.304 | -15.601 | 0.3900 | 11 | reject |

The family shows a clear IC-to-residual gap. Some raw and industry-neutral values are large, especially the overheat avoidance and repair/rebound variants, but after size/liquidity/volatility residualization they fall far below the 0.02 residual IC and 0.20 ICIR research thresholds.

## Failure Analysis

The family failed for four reasons:

1. The strongest signal was mostly explained by style and liquidity structure. Residual IC peaked at only 0.0127.
2. Positive residual diagnostics had weak ICIR and weak positive IC rate. They were statistically visible but not strong enough for a tradable research lead.
3. Several dispersion/breakout variants inverted after neutralization, which means they are more likely capturing industry/style beta than stock-level alpha.
4. The full run was expensive, taking materially longer than previous families, so this family needs cached industry-state matrices before any future re-entry.

## Process Decision

Industry breadth-regime translation is hibernated after Round261 as a direct alpha family. Do not expand windows, flip signs, run TopN portfolios, or run reference dedup from this family because there were zero full-sample residual research leads.

The usable lesson is methodological: industry breadth and dispersion are valuable control/regime descriptors, but not enough as standalone CN stock alpha under the current residual gate. Round262 must rotate to a new orthogonal family. Final holdout remains blocked.

