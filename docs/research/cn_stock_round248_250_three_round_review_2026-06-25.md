# CN Stock Round248-250 Three-Round Review

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Review window: Round248, Round249, Round250
- Decision: rotate family after residual audit failure
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## What Was Tried

Round248 rotated away from realized financial-statement formula mutations after Round245-247 produced zero usable leads. The new family was nonfinancial event context:

- Buyback event strength plus underreaction or quiet-volume context.
- Holder-number contraction plus underreaction or low-volatility context.
- Same parameters across the 2015-2025 long cycle.
- No portfolio grid or final holdout access.

Round249 tested whether the Round248 leads were distinct from raw event signals, context-only legs, and public low-volatility/reversal references.

Round250 residualized each Round248/Round249 lead against its Round249 high-redundancy reference cluster and retested only the residual.

## Results

| Round | Stage | Candidates / Leads | Pass | Promotion |
|---:|---|---:|---:|---:|
| 248 | long-cycle prescreen | 4 factors, 8 horizons, 6 research leads | 6 research leads | 0 |
| 249 | reference dedup | 6 leads | 0 dedup pass | 0 |
| 250 | residual audit | 6 leads | 0 residual pass | 0 |

Round248 looked like progress because several IC metrics were strong. The best raw prescreen result was `event_holder_contraction_low_vol_20` at 20 days with IC 0.0843, ICIR 0.463, t-stat 18.71, and 69.9% positive IC rate.

Round249 and Round250 explain why those numbers are not promotable:

- Holder contraction low-vol and underreaction are mostly raw holder contraction plus context/public low-vol reversal exposure.
- Repurchase underreaction is mostly raw repurchase plus context underreaction.
- Repurchase quiet-volume has some residual IC, but it is too unstable by year and too sparse before 2018.

## Most Important Evidence

- Round249 dedup pass: 0 of 6.
- Round250 residual pass: 0 of 6.
- Holder-related residual median R2: 1.0000 against the selected reference cluster.
- Holder-related residual IC observations after variance filtering: 0.
- Repurchase quiet-volume 20d residual IC: 0.0740, ICIR 0.449, t-stat 4.17, IC>0 64.0%, but failed 2 calendar years.
- Repurchase quiet-volume 5d residual IC: 0.0356, ICIR 0.191, t-stat 1.77, IC>0 54.7%, failed 4 calendar years.
- Event live fetch drift appeared between Round249 and Round250, so event endpoint snapshots must be cached or audited before reuse.

## Audit Conclusion

This was not a profitable discovery. It was a useful process correction.

The optimized workflow successfully prevented a statistically attractive but redundant factor family from reaching walk-forward or portfolio testing. The result is harsh but healthy: 6 apparent leads, 0 independent residual leads, 0 promotable factors.

The failure mode is now specific, not vague:

- The formula design used weighted combinations of components that were later used as references.
- The holder leads had nearly no independent variation after reference regression.
- The repurchase quiet-volume residual was not stable across calendar years.
- Live event-fetch drift adds reproducibility risk.

## Decision

- Hibernate `event_contextual_underreaction` raw event plus context weighted blends.
- Do not tune windows, weights, or top-N portfolios for this family.
- Do not run walk-forward or final holdout on these leads.
- Round251 must rotate to a different family or a genuinely orthogonal event mechanism.

## Round251 Startup Requirements

- Read Round250 residual audit before starting.
- Confirm `round250_zero_residual_pass`.
- Confirm this family is hibernated.
- Confirm event data snapshot caching or coverage audit before any future event-family reuse.
- Select a new hypothesis class before candidate generation.
