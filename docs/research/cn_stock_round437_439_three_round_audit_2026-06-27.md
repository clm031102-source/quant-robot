# CN Stock Round437-439 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Rounds Covered

- Round437: statistical reality check for delayed-exit baseline and quarter-end defensive lanes.
- Round438: public technical indicator quick screen on the delayed-exit lane.
- Round439: formal cohort-entry rebuild for the best Round438 return-enhancement lead, RSRS z top10.

## What Worked

Round437 improved the promotion discipline. It showed that the current delayed-exit pack is simulation-observation eligible, but not statistically final alpha:

- deflated-Sharpe pass count: 6 of 6;
- FDR-significant count: 0 of 6;
- best q-value: about 0.064 for `cost10_zero_qe`;
- best robustness lane: `cost10_zero_qe`.

Round438 found two useful public-indicator leads:

- return-enhancement projection: `tilt_public_rsrs_z_top10`;
- defensive projection: `cash_public_anti_supertrend_top10`.

Round439 prevented a bad promotion. It formally rebuilt RSRS z top10 and showed that the projection uplift was not robust.

## What Failed

RSRS z top10 looked good in the Round438 template projection but failed the formal rebuild:

| Metric | Base | Formal RSRS z Top10 | Direction |
|---|---:|---:|---|
| Annualized return | 6.663% | 6.337% | worse |
| Total return | 218.46% | 201.42% | worse |
| Overlap Sharpe | 0.496 | 0.477 | worse |
| Max drawdown | -26.21% | -27.11% | worse |
| OOS strict pass | 90.00% | 76.67% | worse |
| Beta-hedged annualized return | 7.502% | 7.095% | worse |

Root cause:

- the projection method is useful for quick triage but can overstate incremental effects;
- cohort-level timing, duplicate exit-date handling, delayed-exit repair, vol targeting, and self-risk exposure all interact with the raw public-factor tilt;
- a candidate that improves aggregate period returns can still fail once rebuilt from trade rows.

## Direction Change

Do not continue mining RSRS variants by tuning top fractions or multipliers. That would likely chase the same projection artifact.

Next direction:

1. Formally rebuild the defensive anti-supertrend cash overlay, because its projected value was risk control rather than pure return boost.
2. If anti-supertrend fails, rotate away from public technical overlays.
3. Keep the current delayed-exit baseline as the default paper-simulation candidate unless a formally rebuilt candidate beats it on full-sample, OOS, block, beta, and statistical gates.

## Process Rule Added

Every public-indicator lead now has two statuses:

- projection lead: allowed only for triage;
- formal rebuild candidate: allowed to enter simulation-shortlist discussion only after cohort-entry rebuild.

Projection leads cannot be described as paper-ready, even if their quick-screen annualized return is higher.
