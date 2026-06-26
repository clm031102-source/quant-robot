# CN Stock Round265 Public Tradeable Indicator Composite Residual Prescreen

Date: 2026-06-26

## Scope

Round265 executed the required long-cycle residual prescreen for the 8 frozen Round264 public tradeable indicator composite candidates. This is CN stock cross-sectional factor mining only, not CN ETF rotation.

This round is not a Sharpe, total-return, win-rate, paper, or live-trading claim. Portfolio grids and promotion remained blocked.

## Execution

- Entrypoint: `scripts/run_public_tradeable_indicator_composite_residual_prescreen.py`
- Output: `data/reports/round265_public_tradeable_indicator_composite_residual_prescreen_20260626/`
- Window: 2015-01-05 through 2025-12-31
- Final holdout: excluded
- Assets: 5,707
- Bar rows: 10,785,537
- Candidate tests: 8 factor x 5-day horizon tests
- Factor rows: 80,511,844
- Industry-neutral rows: 77,598,202
- Residual rows: 77,400,146
- Reference factor rows: 60,479,843
- 2015 diagnostics: present for all 8 candidates

Round265 also fixed a performance issue in the Round265 loader: the first full run timed out because a generic loader scanned non-bar processed inputs under `market=CN`. The new Round265 loader reads only the `processed/bars` tree, reducing the input scan from processed moneyflow/factor-input files plus bars to the actual bar files needed by this family.

## Result

- Residual research leads: 0
- Portfolio preflight candidates: 0
- Promotion allowed candidates: 0
- Portfolio grid allowed candidates: 0
- Next direction: `round266_rotate_after_public_tradeable_indicator_composite_residual_prescreen_failure`

The family failed the long-cycle residual prescreen. It should be hibernated unless a genuinely new orthogonal data source or mechanism is introduced.

## Candidate Results

| Factor | Family | Raw IC | Neutral IC | Residual IC | Residual ICIR | Q5-Q1 | Mono | Top Turnover | 2015 IC | Main blockers |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `mfi_cmf_exhaustion_reversal_liquid_14_20` | trend exhaustion/reversal | 0.0171 | 0.0192 | 0.0175 | 0.269 | -0.0213 | 0.50 | 29.5% | 0.0364 | neutral/residual IC below gate, negative quantile spread, style exposure, yearly instability |
| `volume_dryup_pullback_liquid_reversal_5_20` | volume-price absorption | 0.0407 | 0.0412 | 0.0172 | 0.224 | 0.0074 | 0.75 | 46.6% | 0.0510 | residual mean IC below 0.02 gate |
| `adx_efficiency_momentum_quality_14_20` | risk-adjusted momentum | -0.0274 | -0.0253 | -0.0009 | -0.016 | 0.0018 | 0.25 | 16.5% | -0.0208 | negative/weak residual IC, weak monotonicity, style exposure, 2015 failure |
| `supertrend_pullback_absorption_quality_10_3_20` | trend exhaustion/reversal | -0.0112 | -0.0101 | -0.0022 | -0.036 | -0.0045 | 0.75 | 23.9% | 0.0073 | negative residual IC, negative spread, yearly instability |
| `obv_cmf_absorption_reversal_quality_20` | volume-price absorption | -0.0121 | -0.0117 | -0.0093 | -0.172 | -0.0175 | 0.50 | 22.1% | -0.0093 | negative residual IC, negative spread, 2015 failure |
| `donchian_atr_compression_breakout_efficiency_20` | volatility compression/breakout | -0.0473 | -0.0446 | -0.0155 | -0.173 | 0.0170 | 0.75 | 14.9% | -0.0353 | negative residual IC, style exposure, 2015 failure |
| `macd_rsi_momentum_exhaustion_quality_14_26` | risk-adjusted momentum | -0.0473 | -0.0468 | -0.0182 | -0.239 | -0.0089 | 0.50 | 27.0% | -0.0522 | negative residual IC, negative spread, 2015 failure |
| `atr_bandwidth_compression_breakout_quality_20` | volatility compression/breakout | -0.0145 | -0.0156 | -0.0187 | -0.199 | -0.0068 | 0.50 | 12.3% | -0.0368 | negative residual IC, style exposure, 2015 failure |

## Interpretation

The best raw signal was `volume_dryup_pullback_liquid_reversal_5_20`, with raw IC 0.0407 and industry-neutral IC 0.0412. It still failed because the residual IC after industry, size, liquidity, and volatility controls fell to 0.0172, below the 0.02 gate. This is not enough to justify a portfolio grid.

The strongest-looking 2015 rows are not enough to promote anything. The gate is intentionally based on full-window residual IC, quantile shape, turnover, style exposure, reference overlap, and yearly stability, because 2015 can create misleading cycle-specific signals.

The public indicator composite direction did not produce an incremental, robust CN stock alpha. Continuing to tune MFI, CMF, OBV, SuperTrend, MACD, RSI, ATR, or Donchian windows would be parameter mining after a zero-lead residual failure.

## Decision

- Hibernate `public_tradeable_indicator_composite_after_round265_zero_residual_leads`.
- Block direct portfolio grids for `volume_dryup_pullback_liquid_reversal_5_20` despite its raw/neutral IC.
- Block re-entry into single MFI/OBV/SuperTrend/MACD/RSI style parameter sweeps.
- Round266 must rotate to a new orthogonal family and pass the candidate plan gate before any prescreen.
