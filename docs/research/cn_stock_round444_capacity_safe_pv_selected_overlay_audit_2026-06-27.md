# CN Stock Round444 Capacity-Safe PV Selected Overlay Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round444 tests whether other capacity-safe price-volume candidates improve on the Round442 range-contraction increment. This is a controlled family check, not a broad grid.

Tested factors:

- `bollinger_reversal_lowvol_liquid_20`
- `amount_stability_reversal_5_20`
- `pv_corr_reversal_capacity_safe_20`

All were run as top 10%, 1.50x incremental overlays on the current delayed-exit Alpha101/Dragon base, using existing `pre_overlay_return_contribution` and `pre_overlay_target_weight`.

## Coverage

All three selected factors had the same clean shortlist coverage:

- target trade pairs: 26,450;
- matched values: 26,400;
- missing share: 0.189%.

## Result

| Candidate | Annualized | Total Return | Overlap Sharpe | Max DD | Win Rate | Decision |
|---|---:|---:|---:|---:|---:|---|
| Base delayed-exit | 6.663% | +218.46% | 0.496 | -26.21% | 41.33% | Keep default reference |
| Round442 `range_q10_m150` | 7.083% | +241.70% | 0.505 | -26.99% | 41.99% | Current best robust increment |
| `bollinger_reversal_lowvol_liquid_20` | 6.950% | +234.18% | 0.493 | -27.69% | 41.66% | Reject versus Round442 |
| `amount_stability_reversal_5_20` | 6.792% | +225.44% | 0.484 | -28.08% | 41.33% | Reject |
| `pv_corr_reversal_capacity_safe_20` | 6.914% | +232.15% | 0.493 | -27.54% | 41.33% | Reject versus Round442 |

## Interpretation

The same low-volatility reversal cluster has useful information, but merely swapping the expression does not improve the current best lane.

`bollinger_reversal_lowvol_liquid_20` and `pv_corr_reversal_capacity_safe_20` both improve annualized return versus the base, but their overlap Sharpe is weaker than the base and weaker than Round442. `amount_stability_reversal_5_20` is weaker across both return and overlap quality.

## Decision

Reject all three Round444 candidates as promoted simulation candidates.

Do not continue broad low-volatility reversal expression hopping. The next useful action is limited sensitivity on the already-winning `range_contraction_lowvol_reversal_20` overlay.
