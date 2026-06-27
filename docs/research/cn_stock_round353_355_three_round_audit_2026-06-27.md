# CN Stock Round353-355 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

This audit covers the next required three-round block:

- Round353: selected-basket secondary filter quickscreen;
- Round354: PS filter cost/beta quickcheck;
- Round355: shortlist return-overlap audit.

2026 final holdout remains sealed.

## Results

| Round | Direction | Result | Decision |
|---|---|---|---|
| 353 | Use daily-basic fields as secondary filters inside the primary low-turnover basket | `cash_ps_high20_selected + zz500 50%` improved defensive overlap/drawdown profile | Advance PS filter to cost/beta quickcheck |
| 354 | Cost/beta quickcheck for PS filter | 10 bps total +119.29%, ann +4.86%, overlap 0.573, DD -15.90%; CSI500 hedged overlap 0.943 | Add as defensive observation lane |
| 355 | Return overlap among five shortlist candidates | Correlations are high; shortlist is one primary signal family with risk variants | Keep as simulation lane stack, not independent alpha count |

## Useful Output

New candidate added:

`primary_ps_filtered_defensive_zz500`

Formula sketch:

`primary_high_return + cash selected entries in top 20% selected-basket ps_ttm + zz500_mom120_neg_half`

Evidence:

| Metric | Value |
|---|---:|
| Total return | +119.29% |
| Annualized return | +4.86% |
| Sharpe | 1.076 |
| Overlap Sharpe | 0.573 |
| Max drawdown | -15.90% |
| Mean OOS annualized return | +5.01% |
| Worst OOS drawdown | -12.02% |
| 30 bps cost total return | +96.15% |
| 30 bps strict pass | 76.67% |
| CSI500 beta R2 | 0.226 |
| CSI500 beta-hedged annualized return | +4.83% |
| CSI500 beta-hedged overlap Sharpe | 0.943 |

## Honest Limitation

The PS-filtered candidate is not a new independent alpha family.

It is highly correlated with the existing defensive candidate:

| Pair | Pearson Corr. |
|---|---:|
| `primary_defensive_zz500` vs `primary_ps_filtered_defensive_zz500` | 0.988 |
| `primary_high_return` vs `primary_ps_filtered_defensive_zz500` | 0.943 |

Therefore it should be counted as a defensive construction variant, not a standalone new factor discovery.

## Direction Adjustment

Keep working on:

- robust variants of the primary low-turnover/replacement framework;
- risk overlays that are observable before the decision date;
- cost/beta/capacity validation;
- drawdown-aware simulation lane design.

Do not over-count:

- 100%, 75%, 50%, PS-filtered, and safer variants are not five independent alpha families.

Next family work should be genuinely orthogonal:

- event/expectation source with enough PIT coverage;
- industry/sector breadth or regime features not directly derived from the selected basket;
- or a portfolio construction/risk-control improvement that is explicitly labelled as construction, not alpha.

## Current Conclusion

The sprint produced one practical improvement in this block: a PS-filtered defensive observation lane. It is useful for simulation comparison because it offers the best defensive score and strongest overlap-adjusted behavior, but it should not replace the higher-return and default defensive lanes before paper/simulation review.
