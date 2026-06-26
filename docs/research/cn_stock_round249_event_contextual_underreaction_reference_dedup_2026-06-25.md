# CN Stock Round249 Event Contextual Underreaction Reference Dedup

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Stage: `event_contextual_underreaction_reference_dedup`
- Source prescreen: `docs/research/cn_stock_round248_event_contextual_underreaction_prescreen_2026-06-25.md`
- Output: `data/reports/round249_event_contextual_underreaction_reference_dedup_20260625`
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round248 found 6 research-lead factor-horizon combinations. Round249 tested whether those leads were actually independent from:

- Raw event legs: repurchase amount and holder-number contraction.
- Context-only legs: underreaction, quiet volume, and low volatility.
- Public price-volume references: low-volatility reversal, range contraction, Bollinger/RSI/Donchian pullback, price-volume blends, and amount-stability reversal.

This is a pre-portfolio gate. It does not compute Sharpe, total return, annual return, win rate, drawdown, or live/paper readiness.

## Data

- Bars: 2015-01-05 to 2025-12-31.
- Bar assets: 5,707.
- Bar rows: 10,785,537.
- Event rows:
  - `repurchase`: 14,293.
  - `stk_holdernumber`: 232,209.
- Round248 lead factor rows: 424,435.
- Reference rows: 61,372,005.
- Reference factors: 12.
- Labels: 21,417,227.
- Correlation sampling: every 5th signal date for reference correlations only.
- IC and yearly stability: all available signal dates.
- Minimum reference correlation observations: 5.

## Gate Result

- Leads tested: 6.
- Dedup pass: 0.
- Blocked leads: 6.
- Highly redundant lead count: 6.
- Yearly failure lead count: 3.
- Promotion-ready factors: 0.
- Portfolio-grid allowed: 0.
- Next direction: `round250_hibernate_or_orthogonalize_event_contextual_underreaction_after_dedup_failure`.

| Lead | H | IC | ICIR | IC>0 | Main Blockers |
|---|---:|---:|---:|---:|---|
| `event_holder_contraction_low_vol_20` | 20 | 0.0843 | 0.463 | 69.9% | high redundancy with low-vol context, raw holder contraction, range-contraction low-vol reversal |
| `event_repurchase_underreaction_20` | 20 | 0.0823 | 0.455 | 69.0% | high redundancy with raw repurchase/context underreaction; yearly instability; pre-2018 coverage gap |
| `event_repurchase_quiet_volume_20` | 20 | 0.0819 | 0.520 | 70.0% | high redundancy with quiet-volume context; yearly instability; pre-2018 coverage gap |
| `event_holder_contraction_underreaction_20` | 5 | 0.0635 | 0.374 | 65.8% | high redundancy with underreaction context, raw holder contraction, Bollinger/Donchian/amount-stability reversal |
| `event_holder_contraction_low_vol_20` | 5 | 0.0603 | 0.324 | 63.0% | high redundancy with low-vol context, raw holder contraction, range-contraction low-vol reversal |
| `event_repurchase_quiet_volume_20` | 5 | 0.0514 | 0.320 | 62.7% | high redundancy with quiet-volume context; yearly instability; pre-2018 coverage gap |

## Most Important Redundancy Evidence

| Lead | Reference | Obs | Mean Abs Corr | Max Abs Corr | Class |
|---|---|---:|---:|---:|---|
| `event_holder_contraction_low_vol_20` | `context_holder_low_vol_20` | 328 | 0.7546 | 1.0000 | highly redundant |
| `event_holder_contraction_low_vol_20` | `raw_event_holder_number_contraction_2q` | 328 | 0.5513 | 0.9025 | highly redundant |
| `event_holder_contraction_low_vol_20` | `range_contraction_lowvol_reversal_20` | 319 | 0.5489 | 0.9331 | highly redundant |
| `event_repurchase_underreaction_20` | `raw_event_repurchase_amount_to_mv_20` | 26 | 0.6519 | 0.9136 | highly redundant |
| `event_repurchase_underreaction_20` | `context_repurchase_pre_signal_underreaction_20` | 26 | 0.6503 | 0.9429 | highly redundant |
| `event_repurchase_quiet_volume_20` | `context_repurchase_quiet_volume_20` | 18 | 0.5712 | 0.9726 | highly redundant |
| `event_holder_contraction_underreaction_20` | `context_holder_pre_signal_underreaction_20` | 333 | 0.7090 | 1.0000 | highly redundant |
| `event_holder_contraction_underreaction_20` | `raw_event_holder_number_contraction_2q` | 333 | 0.5133 | 0.9683 | highly redundant |
| `event_holder_contraction_underreaction_20` | `bollinger_reversal_lowvol_liquid_20` | 327 | 0.4700 | 0.8556 | highly redundant |

## Interpretation

Round248 looked promising because the IC layer improved dramatically relative to raw Round147 event factors. Round249 explains why that improvement should not be trusted as standalone alpha:

- Holder contraction low-vol is mostly the low-vol context leg plus raw holder contraction.
- Holder contraction underreaction is mostly the underreaction leg plus raw holder contraction and public reversal/low-vol references.
- Repurchase underreaction is mostly raw repurchase plus the underreaction context leg.
- Repurchase quiet-volume has a weak event-date sample and no adequate pre-2018 coverage under the current cross-section gate.

This does not mean the work was useless. It means the new process worked: the project found a statistically attractive lead, then prevented it from being promoted once the lead was shown to be redundant.

## Decision

- Promote to walk-forward: 0.
- Promote to paper-ready: 0.
- Keep for library: no canonical factor from Round248/249.
- Hibernate current formulas unless a new orthogonal residualized hypothesis is written first.

## Next Action

Round250 must not expand these formulas by parameter tuning. Allowed paths:

- Residualize the event-context leads against raw event, context-only, and public low-vol/reversal references, then re-run IC and yearly stability.
- Or hibernate this family and rotate to a new public-method or event family with a genuinely orthogonal mechanism.

Blocked paths:

- No portfolio grid on Round248 lead formulas.
- No walk-forward on non-deduped formulas.
- No further raw event + low-vol/underreaction weighted blends without residualization.
- No final-holdout read.
