# CN Stock Public Reference Multi-Family Prescreen - Round128

## Scope

- Machine role: office_desktop factor validation.
- Market and asset: CN stock cross-sectional alpha.
- Input preregistration: `docs/research/cn_stock_public_reference_multi_family_preregistration_round127_2026-06-22.md`.
- Data window: 2015-01-05 to 2023-07-31.
- Final holdout: not included.
- Stage: long-cycle IC, quantile, turnover, and multiple-testing prescreen only.

## Run Evidence

- Command output root: `data/reports/public_reference_multi_family_prescreen_round128_20260622`.
- Bars: 7,643,870 rows, 5,418 assets.
- Candidates: 20.
- Families: 9.
- Horizons: 5, 10, 20.
- Factor x horizon tests: 60.
- Streaming evaluation: true.
- Factor rows evaluated: 138,168,657.
- Aligned rows evaluated: 410,857,892.
- FDR-significant tests: 54.
- Research leads: 3.
- Portfolio backtest allowed candidates: 0.
- Promotion allowed candidates: 0.

## Research Leads

All three research leads came from the same preregistered factor:

| Factor | Family | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Top turnover |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alpha101_rank_pv_reversal_liquid_20 | public_formula_alpha101 | 20 | 0.0489 | 0.526 | 23.85 | 69.1% | 0.0089 | 0.900 | 17.5% |
| alpha101_rank_pv_reversal_liquid_20 | public_formula_alpha101 | 10 | 0.0453 | 0.496 | 22.55 | 69.8% | 0.0057 | 0.900 | 17.5% |
| alpha101_rank_pv_reversal_liquid_20 | public_formula_alpha101 | 5 | 0.0431 | 0.471 | 21.44 | 68.4% | 0.0037 | 0.900 | 17.5% |

Interpretation: this is a real statistical lead, not a promotion. It must next pass family-level de-duplication, inverse-direction checks, walk-forward, costs, capacity, regime coverage, and portfolio conversion before it can be treated as a paper candidate.

## Important Negative Evidence

Many public trend/breakout style candidates were strongly significant in the negative direction:

- `donchian_breakout_efficiency_liquid_20`: IC -0.0967 at 20d, monotonicity -1.000.
- `qlib_alpha158_price_efficiency_liquid_20`: IC -0.0840 at 20d, monotonicity -1.000.
- `qlib_alpha158_volume_price_resonance_20_60`: IC -0.0697 at 20d.
- `rsrs_slope_acceleration_quality_18_60`: IC -0.0452 at 20d.
- `supertrend_pullback_lowvol_liquid_10_3`: IC -0.0502 at 20d.

This is useful evidence, but not immediate alpha. Any inverse use must be preregistered and reviewed because turning a failed positive signal upside down after seeing results is a fresh hypothesis.

## Engineering Note

The first full run was too heavy because it attempted a giant long factor table. Round128 was repaired to use streaming factor evaluation:

- Feature table is computed once.
- Forward returns are attached directly by asset time series.
- Each factor is evaluated one at a time.
- Multiple-testing correction is still applied across all 20 candidates x 3 horizons.

## Decision

- Promotable factors: 0.
- Research leads: 1 unique factor, 3 horizons.
- Next required direction: `round129_round126_128_three_round_review_before_next_action`.
- Do not run a portfolio grid yet.
- Do not lock into Alpha101 only before the three-round review audits redundancy, inverse-direction temptation, and portfolio translation risk.
