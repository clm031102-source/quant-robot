# CN Stock Bottom-Exclusion Overlay Round 51 - 2026-06-21

## Purpose

Round48 showed that three public price-volume formula factors keep strong within-industry RankIC.
Round49 showed that the same factors still fail as long-only TopN portfolios.

Round51 tests the only justified translation-layer follow-up from Round49:

- do not tune formula parameters,
- do not expand raw TopN grids,
- treat the factors as tail-risk exclusion signals,
- compare full cross-sectional mean forward return with the mean after excluding the bottom 20% ranked stocks.

This is a diagnostic overlay audit, not a promotable portfolio backtest.

## Public-Method Anchor

The method follows the spirit of public quant research workflows:

- Alphalens-style factor analysis: inspect quantile returns and IC before claiming tradability.
- Qlib-style workflow discipline: keep data, signal, evaluation, and reporting reproducible from config.
- Vectorbt-style fast experiment design: use vectorized diagnostics before slower portfolio translation.

References:

- https://github.com/quantopian/alphalens
- https://github.com/microsoft/qlib
- https://github.com/polakowo/vectorbt

## Tooling Added

Reusable audit module:

- `src/quant_robot/ops/bottom_exclusion_overlay_audit.py`

Runner:

- `scripts/run_bottom_exclusion_overlay_audit.py`

Tests:

- `tests/unit/test_bottom_exclusion_overlay_audit.py`
- `tests/unit/test_bottom_exclusion_overlay_audit_cli.py`

Startup gate hardening:

- default translation-layer protocol now requires:
  - `bottom_exclusion_overlay_audit_for_strong_ic_rejected_topn`
  - `bottom_exclusion_costed_walk_forward_before_promotion`
  - `bottom_exclusion_overlay_audit_read`
  - `bottom_exclusion_costed_walk_forward_registered`

## Experiment

Base config:

```powershell
configs\experiment_grid_cn_stock_public_formula_price_volume_industry_neutral_round49_20260621.json
```

rebalance=5 command:

```powershell
python scripts\run_bottom_exclusion_overlay_audit.py `
  --grid-config configs\experiment_grid_cn_stock_public_formula_price_volume_industry_neutral_round49_20260621.json `
  --rebalance-interval 5 `
  --output-dir data\reports\bottom_exclusion_overlay_public_formula_round51_20260621_reb5
```

rebalance=10 command:

```powershell
python scripts\run_bottom_exclusion_overlay_audit.py `
  --grid-config configs\experiment_grid_cn_stock_public_formula_price_volume_industry_neutral_round49_20260621.json `
  --rebalance-interval 10 `
  --output-dir data\reports\bottom_exclusion_overlay_public_formula_round51_20260621_reb10
```

Parameters:

- Market: CN stocks
- Period: 2015-01-05 through 2025-12-31
- Horizon: 20 trading days
- Execution lag: 1
- Bottom exclusion: 20%
- Factors: the same three public formula price-volume factors from Round49

## Results

### Rebalance 5

| Factor | Classification | Dates | Full Mean | Kept Mean | Bottom Mean | Overlay Excess | t-stat | Positive Rate | Kept Compounded | Full Compounded |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `formula_volume_contraction_reversal_20` | bottom-exclusion candidate | 530 | 0.0066 | 0.0093 | -0.0043 | 0.0027 | 10.34 | 0.69 | 18.1315 | 3.3280 |
| `formula_pv_corr_reversal_20` | bottom-exclusion candidate | 530 | 0.0066 | 0.0085 | -0.0009 | 0.0019 | 8.19 | 0.68 | 11.8192 | 3.3280 |
| `formula_range_contraction_breakout_20` | weak/unproven exclusion | 530 | 0.0066 | 0.0070 | 0.0048 | 0.0004 | 1.33 | 0.56 | 5.5276 | 3.3280 |

### Rebalance 10

| Factor | Classification | Dates | Full Mean | Kept Mean | Bottom Mean | Overlay Excess | t-stat | Positive Rate | Kept Compounded | Full Compounded |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `formula_volume_contraction_reversal_20` | bottom-exclusion candidate | 265 | 0.0070 | 0.0098 | -0.0040 | 0.0028 | 7.62 | 0.69 | 3.6743 | 1.2049 |
| `formula_pv_corr_reversal_20` | bottom-exclusion candidate | 265 | 0.0070 | 0.0091 | -0.0012 | 0.0021 | 6.42 | 0.70 | 3.0062 | 1.2049 |
| `formula_range_contraction_breakout_20` | weak/unproven exclusion | 265 | 0.0070 | 0.0074 | 0.0057 | 0.0003 | 0.72 | 0.56 | 1.6482 | 1.2049 |

## Interpretation

The useful finding changed shape:

- These factors remain bad as direct buy-list TopN signals.
- `formula_volume_contraction_reversal_20` has the strongest evidence as a tail-risk exclusion signal.
- `formula_pv_corr_reversal_20` is also a plausible exclusion/risk-control signal.
- `formula_range_contraction_breakout_20` should not receive more budget in this translation path.

The compounded kept/full figures are diagnostic only because the 20-day horizon overlaps across signal dates. They are not a deployable equity curve.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads: 2 risk-filter candidates:

- `formula_volume_contraction_reversal_20`
- `formula_pv_corr_reversal_20`

Do not promote either candidate without costed walk-forward validation.

## Next Direction

Round52 should implement a costed, benchmark-aware walk-forward test for bottom-exclusion risk filters:

- use `volume_contraction` first, `pv_corr` second,
- keep bottom 20% exclusion frozen,
- no formula parameter tuning,
- compare against broad equal-weight or benchmark-like exposure,
- include costs, turnover, capacity, drawdown, overlap-aware statistics, and regime coverage,
- reject if the effect disappears after costs or walk-forward split.
