# CN Stock Round224 Financial PIT Gap Reversal Walk-Forward Preflight

- Date: 2026-06-24
- Machine/task: office_desktop / factor_validation
- Stage: financial_pit_post_announcement_gap_reversal_reference_dedup_walk_forward_preflight
- Input evidence: Round223 financial PIT gap reversal residual prescreen
- Status: cleared for walk-forward preflight only
- Promotion allowed: false
- Live boundary allowed: false

## Result

Round223 produced 5 residual research leads and 0 promotable factors. Round224 added candidate-cluster deduplication before any portfolio grid or Sharpe/profit claim.

- Residual research leads: 5
- Candidate pair correlation rows: 10
- Max candidate absolute cross-sectional Spearman correlation: 0.996
- Cluster duplicates: 2
- Frozen walk-forward candidates: 3
- Promotion candidates: 0
- Next direction: `round225_financial_pit_post_announcement_gap_reversal_walk_forward_cost_capacity_regime_validation`

## Frozen Candidates

| Factor | IC | t | Ref Corr | Candidate Corr | Status |
|---|---:|---:|---:|---:|---|
| `pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` | 0.1383 | 4.01 | 0.697 | 0.000 | frozen |
| `pead_gap_overreaction_reversal_volume_confirmed_1_5` | 0.1069 | 2.79 | 0.689 | 0.929 | frozen |
| `pead_gap_overreaction_reversal_quality_conditioned_1_5` | 0.0654 | 2.28 | 0.578 | 0.305 | frozen |

## Deduped Variants

| Factor | IC | t | Candidate Corr | Representative |
|---|---:|---:|---:|---|
| `pead_gap_overreaction_reversal_1_5` | 0.1240 | 3.43 | 0.972 | `pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` |
| `pead_gap_overreaction_reversal_size_neutral_candidate_1_5` | 0.1219 | 3.41 | 0.971 | `pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` |

## Walk-Forward Plan

- Fold 1: train 2015-01-01 to 2018-12-31, test 2019-01-01 to 2020-12-31
- Fold 2: train 2015-01-01 to 2020-12-31, test 2021-01-01 to 2022-12-31
- Fold 3: train 2015-01-01 to 2022-12-31, test 2023-01-01 to 2024-12-31
- Fold 4: train 2015-01-01 to 2024-12-31, test 2025-01-01 to 2025-12-31

## Controls

- Uses PIT financial signal dates from `data/processed/round202_financial_pit_signal_filtered_20260623`.
- Blocks final holdout use until walk-forward, cost/capacity, regime, and OOS gates clear.
- Freezes TopN, holding period, rebalance interval, cost, and capital stress policy before validation.
- Requires CN stock portfolio construction policy and China market regime controls.

## Conclusion

This is the first useful repair after Round222 rejected the wrong-signed PEAD underreaction line. It does not prove tradability. It only proves that 3 non-identical gap-reversal candidates are eligible for Round225 walk-forward, cost/capacity, and regime validation.
