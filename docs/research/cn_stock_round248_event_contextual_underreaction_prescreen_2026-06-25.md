# CN Stock Round248 Event Contextual Underreaction Prescreen

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Stage: `event_contextual_underreaction_prescreen`
- Config: `configs/factor_mining_candidate_plan_round248_event_contextual_underreaction_20260625.json`
- Output: `data/reports/round248_event_contextual_underreaction_prescreen_20260625`
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Why This Round Was Run

Round245-247 kept mutating realized financial-statement formulas and produced zero usable research leads. The startup method gate was updated to force a family rotation before new mining. Round248 therefore rotated into a nonfinancial event context family:

- Buyback event strength plus underreaction / quiet-volume context.
- Holder-number contraction plus underreaction / low-volatility context.
- No dividend-yield variants after Round148 showed dividend was mostly public value/dividend exposure.
- No dragon-tiger variants after Round232-233 failed size-residual shape.
- No realized statement formula mutations after Round245-247.

## Data And PIT Policy

- Bars: CN stock long-cycle data from 2015-01-05 to 2025-12-31.
- Bar assets: 5,707.
- Bar rows: 10,785,537.
- Event endpoints:
  - `repurchase`: 14,293 rows.
  - `stk_holdernumber`: 232,209 rows.
- Factor rows after PIT signal-date mapping and context construction: 424,435.
- Labels: 21,417,227 rows.
- Aligned rows: 841,022.
- Signal date: first tradable date strictly after event date plus configured PIT lag.
- Execution: next-trade execution lag.
- Final holdout: 2026 remains blocked.

## Candidates

| Factor | Formula |
|---|---|
| `event_repurchase_underreaction_20` | `0.65*cs_z(repurchase_amount/adv20) + 0.35*cs_z(-pre_signal_return_20)` |
| `event_repurchase_quiet_volume_20` | `0.65*cs_z(repurchase_amount/adv20) + 0.35*cs_z(-amount_trend_5_20)` |
| `event_holder_contraction_underreaction_20` | `0.65*cs_z(-holder_number_change) + 0.35*cs_z(-pre_signal_return_20)` |
| `event_holder_contraction_low_vol_20` | `0.65*cs_z(-holder_number_change) + 0.35*cs_z(-realized_vol_20)` |

## Main Results

- Candidates: 4.
- Tests: 8 factor x horizon tests.
- FDR-significant tests: 8.
- Neutral gate passes: 7.
- Research leads: 6.
- Promotion-ready factors: 0.
- Next direction: `round249_event_contextual_underreaction_reference_dedup_walk_forward_preflight`.

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | SizeNeuIC | Size Retention | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `event_holder_contraction_low_vol_20` | 20 | 0.0843 | 0.463 | 18.71 | 69.9% | 0.0324 | 0.80 | 0.0451 | 0.535 | yes |
| `event_repurchase_underreaction_20` | 20 | 0.0823 | 0.455 | 4.55 | 69.0% | 0.0210 | 0.70 | 0.0508 | 0.617 | yes |
| `event_repurchase_quiet_volume_20` | 20 | 0.0819 | 0.520 | 5.20 | 70.0% | 0.0200 | 0.70 | 0.0570 | 0.695 | yes |
| `event_holder_contraction_underreaction_20` | 5 | 0.0635 | 0.374 | 15.14 | 65.8% | 0.0130 | 0.90 | 0.0543 | 0.856 | yes |
| `event_holder_contraction_low_vol_20` | 5 | 0.0603 | 0.324 | 13.14 | 63.0% | 0.0128 | 0.90 | 0.0359 | 0.595 | yes |
| `event_repurchase_quiet_volume_20` | 5 | 0.0514 | 0.320 | 3.23 | 62.7% | 0.0027 | 0.90 | 0.0355 | 0.691 | yes |
| `event_holder_contraction_underreaction_20` | 20 | 0.0745 | 0.434 | 17.46 | 68.0% | 0.0259 | 0.60 | 0.0575 | 0.773 | no |
| `event_repurchase_underreaction_20` | 5 | 0.0567 | 0.298 | 3.01 | 58.8% | 0.0064 | 0.60 | 0.0348 | 0.613 | no |

## Increment Versus Round147 Raw Events

The context layer improved the previously rejected raw event signals:

- Raw `event_holder_number_contraction_2q` 20d had IC 0.0395, ICIR 0.279, monotonicity 0.10, size-neutral IC 0.0139, no lead.
- Round248 `event_holder_contraction_low_vol_20` 20d improved to IC 0.0843, ICIR 0.463, monotonicity 0.80, size-neutral IC 0.0451, lead.
- Raw `event_repurchase_amount_to_mv_20` 20d had IC 0.0788, ICIR 0.440, size-neutral IC 0.0355, size retention 0.451, no lead.
- Round248 repurchase context factors improved size-neutral retention to 0.617-0.695 and became research leads on the 20d horizon.

## Stability Audit

Holder-number context factors covered all 11 years from 2015-2025 and had no negative calendar year by mean IC. This is materially better than the previous financial-statement mutation rounds.

Stress-period mean IC:

| Factor | H | 2015 crash | 2018 deleveraging | 2020 Covid | 2022 bear | 2024-2025 |
|---|---:|---:|---:|---:|---:|---:|
| `event_holder_contraction_low_vol_20` | 5 | 0.0286 | 0.0325 | 0.0511 | 0.0843 | 0.0621 |
| `event_holder_contraction_low_vol_20` | 20 | 0.0164 | 0.0525 | 0.1411 | 0.1314 | 0.0875 |
| `event_holder_contraction_underreaction_20` | 5 | 0.0580 | 0.0617 | 0.0581 | 0.0599 | 0.0758 |
| `event_holder_contraction_underreaction_20` | 20 | 0.0760 | 0.0768 | 0.1219 | 0.1096 | 0.0989 |

Repurchase context factors are promising but weaker as evidence because they only have enough IC dates from 2018-2025. They do not cover 2015-2017 or 2020 Covid at the configured minimum cross-section. Treat them as secondary leads until a coverage audit explains the missing years.

## Interpretation

This round is the first post-optimization round with meaningful research leads. The key improvement was not more parameter search; it was changing the hypothesis class:

- From stale realized-statement formula mutation.
- To event strength plus price/liquidity context that directly tests whether the event was already priced.

The result is not paper-ready:

- There is no walk-forward validation yet.
- There is no reference de-dup against low-volatility, reversal, value, holder concentration, or liquidity factors yet.
- There is no portfolio construction, Sharpe, drawdown, turnover, win rate, cost, or capacity result yet.
- Repurchase coverage is incomplete before 2018 under the current event cross-section gate.
- The very large industry-neutral IC values need a next-gate audit to rule out event-date clustering or industry-specific announcement-cycle artifacts.

## Decision

- Promote to research lead gate: 6 factor-horizon combinations.
- Promote to paper-ready: 0.
- Run next: `round249_event_contextual_underreaction_reference_dedup_walk_forward_preflight`.
- Keep blocked: portfolio grids, live/manual use, final holdout, and any realized statement formula mutation.
