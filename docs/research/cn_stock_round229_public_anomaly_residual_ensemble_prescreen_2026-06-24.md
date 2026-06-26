# CN Stock Round229 Public Anomaly Residual Ensemble Prescreen - 2026-06-24

## Purpose

Round228 registered four fixed-weight public-anomaly ensemble factors. Round229 ran the required long-cycle residual IC prescreen before any portfolio grid or promotion.

This remains research-only:

- portfolio grid allowed: false;
- promotion allowed: false;
- final holdout: not touched;
- broker/account/order/live trading: not allowed.

## Run

Command:

```powershell
python scripts\run_public_anomaly_residual_ensemble_prescreen.py --sharded --output-dir data\reports\public_anomaly_residual_ensemble_prescreen_round229_20260624
```

The first full run exposed a performance issue: building all public reference factors for every yearly shard dominated runtime. A sharded `reference_mode=defer_until_residual_lead` policy was added so the expensive reference-dedup stage is skipped unless a residual IC lead exists. This is recorded in the report and does not permit promotion.

## Data Window

- Signal window: 2015-01-01 to 2025-12-31.
- Bar rows: 10,785,537.
- Asset count: 5,707.
- Factor rows: 29,425,630.
- Industry-neutral rows: 28,352,754.
- Residual rows: 28,352,754.
- Label rows: 10,777,095.
- Shards: 11 yearly shards.

## Results

| Factor | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | Positive Residual IC | Lead | Main Blockers |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `public_anomaly_residual_equal_weight_20` | 5 | 0.0613 | 0.0589 | 0.0214 | 0.331 | 63.7% | no | high size/liquidity/vol exposure |
| `public_anomaly_residual_regime_conditioned_20` | 5 | 0.0777 | 0.0699 | 0.0210 | 0.321 | 63.7% | no | high size/liquidity/vol exposure |
| `public_anomaly_residual_agreement_20` | 5 | 0.0426 | 0.0394 | 0.0132 | 0.258 | 59.7% | no | residual IC below threshold, high exposure, yearly instability |
| `public_anomaly_residual_disagreement_risk_20` | 5 | 0.0311 | 0.0255 | -0.0037 | -0.080 | 48.2% | no | residual IC/ICIR/positive-rate failure, high exposure, yearly instability |

## Decision

Promotable factors from Round229: 0.

Paper-ready factors from Round229: 0.

Residual research leads from Round229: 0.

The family should rotate instead of parameter tuning. The two strongest raw-IC variants are useful diagnostics: they show public anomaly agreement exists in the raw cross-section, but the signal is not clean enough after exposure checks because it is still too entangled with implementation/style exposures.

## Next Direction

`round230_rotate_after_public_anomaly_residual_ensemble_failure`

Rules for the next round:

- do not tune weights/windows inside `public_anomaly_residual_ensemble_risk_budget`;
- do not run a portfolio grid from these four factors;
- use this result as evidence that raw public anomaly IC is insufficient unless exposure contamination is repaired by a genuinely new mechanism;
- rotate to a new family or a new orthogonal exposure-repair hypothesis.
