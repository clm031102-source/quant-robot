# CN Stock Round250 Event Contextual Underreaction Residual Audit

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Stage: `event_contextual_underreaction_residual_audit`
- Source dedup: `docs/research/cn_stock_round249_event_contextual_underreaction_reference_dedup_2026-06-25.md`
- Output: `data/reports/round250_event_contextual_underreaction_residual_audit_20260625`
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round248 produced 6 attractive event-context research leads. Round249 showed every lead was highly redundant with raw event legs, context-only legs, or public low-volatility/reversal references. Round250 converted that warning into a stricter test:

- Select each Round249 highly redundant reference cluster.
- Regress the Round248 lead cross-sectionally against that cluster on each signal date.
- Re-test only the residual signal against forward returns.
- Block walk-forward and portfolio grids unless the residual keeps independent IC, ICIR, t-stat, positive IC rate, and yearly stability.

## Data

- Bars: 2015-01-05 to 2025-12-31.
- Bar assets: 5,707.
- Bar rows: 10,785,537.
- Event rows in this live fetch:
  - `repurchase`: 12,335.
  - `stk_holdernumber`: 229,329.
- Lead factor rows: 416,152.
- Reference rows: 61,359,064.
- Reference factors: 12.
- Labels: 21,417,227.
- Final holdout: excluded.

Data reproducibility note: Round249's report recorded 14,293 `repurchase` rows and 232,209 `stk_holdernumber` rows from its live Tushare fetch. Round250's fresh fetch returned fewer rows. The residual conclusion is still not permissive, but future event-family reuse should cache or audit the exact event snapshot before comparing rounds.

## Gate Result

- Leads tested: 6.
- Residual pass: 0.
- Blocked leads: 6.
- Promotion-ready factors: 0.
- Portfolio-grid allowed: 0.
- Next direction from the run artifact: `round251_hibernate_event_contextual_underreaction_after_residual_audit_failure`.

| Lead | H | References | Median R2 | Residual IC | ICIR | t | IC>0 | Year Fail | Main Blockers |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `event_holder_contraction_low_vol_20` | 20 | 4 | 1.0000 | 0.0000 | 0.000 | 0.00 | 0.0% | 0 | residual variance collapsed |
| `event_repurchase_underreaction_20` | 20 | 2 | 1.0000 | 0.0000 | 0.000 | 0.00 | 0.0% | 0 | residual variance collapsed |
| `event_repurchase_quiet_volume_20` | 20 | 1 | 0.1949 | 0.0740 | 0.449 | 4.17 | 64.0% | 2 | yearly instability |
| `event_holder_contraction_underreaction_20` | 5 | 6 | 1.0000 | 0.0000 | 0.000 | 0.00 | 0.0% | 0 | residual variance collapsed |
| `event_holder_contraction_low_vol_20` | 5 | 4 | 1.0000 | 0.0000 | 0.000 | 0.00 | 0.0% | 0 | residual variance collapsed |
| `event_repurchase_quiet_volume_20` | 5 | 1 | 0.1949 | 0.0356 | 0.191 | 1.77 | 54.7% | 4 | ICIR, t-stat, IC+ rate, yearly instability |

## Interpretation

The holder-number leads were not independent alpha. Their formulas were weighted combinations of raw holder contraction and context legs, and the Round249 reference cluster explained nearly all cross-sectional variation. Once the reference cluster was removed, residual variance was effectively zero and IC observations disappeared.

The repurchase underreaction lead was also fully explained by raw repurchase plus context underreaction. It has no independent residual signal under this audit.

The only partial survivor was `event_repurchase_quiet_volume_20`, especially at the 20-day horizon. It retained positive residual IC after removing the quiet-volume context reference, but it failed yearly stability in 2019 and 2021. The 5-day version also failed 2018, 2019, 2021, and 2025. This is not enough for walk-forward preflight because the edge is sparse, regime-dependent, and already has a pre-2018 coverage gap.

## Decision

- Promote to walk-forward: 0.
- Promote to paper-ready: 0.
- Keep canonical factor: no.
- Hibernate: all raw event plus underreaction/quiet-volume/low-vol weighted blends from Round248.
- Block: further parameter tuning, portfolio grids, final holdout reads, and walk-forward on these formulas.

## Required Next Action

Round251 must rotate away from this family. Re-entry is allowed only with a genuinely new orthogonal hypothesis and a cached/audited event data snapshot.
