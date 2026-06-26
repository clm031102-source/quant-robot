# CN Stock Public Technical Failure-Reversal Prescreen Round155

## Scope

- Machine/task: office_desktop / factor_validation.
- Market/asset: CN stock cross-sectional alpha.
- Source preregistration: `docs/research/cn_stock_public_technical_failure_reversal_preregistration_round154_2026-06-23.md`.
- Data window: 2015-01-05 to 2025-12-31.
- Final holdout: not included.
- Stage: long-cycle IC/quantile/turnover/FDR prescreen only.

## Run Evidence

| Metric | Value |
|---|---:|
| Bar rows | 10,785,537 |
| Assets | 5,707 |
| Candidates | 8 |
| Families | 5 |
| Horizons | 5, 10, 20 |
| Factor x horizon tests | 24 |
| Factor rows evaluated | 80,458,177 |
| Aligned rows evaluated | 239,703,170 |
| FDR-significant tests | 22 |
| Research leads | 1 |
| Portfolio backtest allowed | 0 |
| Promotion allowed | 0 |

## Research Lead

| Factor | Family | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Top turnover |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `inverse_rsrs_slope_failure_liquid_18_60` | rsrs_failure_reversal | 5 | 0.0334 | 0.409 | 20.98 | 69.1% | 0.0062 | 0.800 | 20.1% |

Interpretation: this is a statistical research lead only. It is not independent alpha yet. The next gate must test industry, size, liquidity, and reference-factor de-duplication before any portfolio grid.

## Important Non-Leads

Several candidates had high raw IC but failed the quantile spread/monotonicity gate:

- `inverse_kbar_momentum_failure_lowvol_20`: best IC 0.0746, but Q5-Q1 was negative and monotonicity was weak/negative.
- `inverse_volume_price_resonance_failure_20_60`: best IC 0.0596, but monotonicity was weak and shorter horizons had negative Q5-Q1.
- `inverse_price_efficiency_failure_liquid_20`: positive IC but ICIR below gate and monotonicity weak.

This matters because high IC alone can hide a poor portfolio translation surface. These candidates should not go to a TopN portfolio grid.

## Engineering Improvement

The first real Round155 run timed out when reusing the full public-reference feature engine. The prescreen was repaired to use a dedicated technical-only feature path. It now avoids loading daily-basic and moneyflow fields that are irrelevant to the 8 Round154 candidates.

## Decision

- Unique research leads: 1.
- Promotable candidates: 0.
- Manual/live candidates: 0.
- Next required direction: `round156_public_technical_failure_reversal_neutral_dedup_before_portfolio_grid`.

Round156 must focus on `inverse_rsrs_slope_failure_liquid_18_60` at 5-day horizon only. It must test industry, size, liquidity, and reference de-duplication before any costed portfolio work.

