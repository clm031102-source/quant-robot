# CN Stock Capacity-Safe Price-Volume Lead Dedup Round103 - 2026-06-22

## Executive Summary

Round103 audited the only Round102 research lead, `bollinger_reversal_lowvol_liquid_20`, before allowing any portfolio grid or walk-forward bridge.

Scope:

- Machine: `office_desktop`
- Market: CN A-share stocks
- Analysis window: 2015-01-01 through 2025-12-31
- Final holdout: 2026 not included
- Lead: `bollinger_reversal_lowvol_liquid_20`
- Lead horizon: 20 trading days
- Bars: 10,785,537 rows across 5,707 assets
- Sampled factor rows: 20,168,889
- Candidates: 10
- Compared candidates: 9
- Correlation observations: 4,784
- Highly redundant candidates: 3
- Moderately redundant candidates: 4
- Unique candidates: 2
- Promotion-allowed factors: 0

## Decision

The Bollinger lead is not advanced to a cost/capacity portfolio bridge in its current form.

Reason:

- It is a valid Round102 statistical lead, but Round103 shows it is highly redundant with several other low-volatility reversal or pullback candidates.
- The lead is therefore more likely a shared low-volatility mean-reversion cluster than a distinct factor worth immediate portfolio-grid spend.

Set next direction to:

```text
round104_family_rotation_after_bollinger_redundancy
```

## Correlation Dedup Results

| Candidate vs Bollinger lead | Observations | Mean corr | Mean abs corr | Max abs corr | Positive rate | Class |
|---|---:|---:|---:|---:|---:|---|
| `donchian_pullback_lowvol_liquid_20` | 533 | 0.4447 | 0.4463 | 0.9702 | 98.9% | highly redundant |
| `rsi_reversal_lowvol_liquid_14_20` | 533 | 0.8178 | 0.8178 | 0.9192 | 100.0% | highly redundant |
| `range_contraction_lowvol_reversal_20` | 533 | 0.5449 | 0.5521 | 0.8568 | 98.5% | highly redundant |
| `amount_stability_reversal_5_20` | 533 | 0.5840 | 0.5851 | 0.8438 | 99.6% | moderately redundant |
| `volume_contraction_reversal_lowvol_20` | 533 | 0.6611 | 0.6614 | 0.8166 | 99.8% | moderately redundant |
| `pv_lowvol_reversal_blend_20` | 533 | 0.5880 | 0.5898 | 0.8038 | 99.1% | moderately redundant |
| `price_volume_trend_quality_20_60` | 523 | -0.4969 | 0.4997 | 0.7691 | 1.3% | moderately redundant |
| `pv_corr_reversal_capacity_safe_20` | 533 | 0.3610 | 0.3614 | 0.6700 | 99.4% | unique |
| `skip5_momentum_lowvol_20` | 530 | -0.1218 | 0.1837 | 0.5268 | 24.3% | unique |

## Interpretation

The Round102 lead was not fake, but it is not scarce information. It sits inside a broad public technical reversal cluster:

- Bollinger reversal,
- RSI reversal,
- Donchian pullback,
- range contraction,
- low-volatility reversal.

The highest maximum absolute correlation reached 0.9702 against `donchian_pullback_lowvol_liquid_20`, and `rsi_reversal_lowvol_liquid_14_20` had mean absolute correlation 0.8178. This is too close to treat the Bollinger line as a fresh alpha family.

The two relatively independent names are not immediate replacement leads:

- `pv_corr_reversal_capacity_safe_20` had weaker Round102 IC and quantile evidence.
- `skip5_momentum_lowvol_20` failed FDR and had weak/negative Round102 evidence.

## Gate Result

Blockers:

- `lead_highly_redundant_with_existing_candidate`

Promotion remains blocked because this stage is only a de-duplication audit. Even a non-redundant result would still need cost/capacity bridge, walk-forward, regime coverage, and holdout discipline.

## Output

Generated report files:

```text
data/reports/capacity_safe_price_volume_lead_dedup_round103_20260622/
```

Generated files under `data/reports` stay out of Git by policy.
