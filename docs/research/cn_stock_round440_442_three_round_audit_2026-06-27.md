# CN Stock Rounds440-442 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Audit the three-round block after the public-technical overlay failures and decide whether the sprint should keep mining the same family or rotate.

## Round Summary

| Round | Work | Outcome | Decision |
|---:|---|---|---|
| 440 | Formal rebuild of anti-SuperTrend cash overlay | Annualized return fell from 6.663% to 5.768%, overlap Sharpe fell from 0.496 to 0.468, OOS strict pass fell from 90.00% to 76.67%, and factor missing share was 83.60%. | Reject public-technical cash overlay. |
| 441 | Add capacity-safe price-volume source support and true incremental overlay mode | `range_contraction_lowvol_reversal_20` source coverage reached 99.81%; the runner can now use existing `pre_overlay_return_contribution` and `pre_overlay_target_weight` without replacing the Alpha101/Dragon base. | Keep the code path; use it only for formal incremental tests. |
| 442 | Formal incremental range-contraction overlay | 10 bps improved annualized return from 6.663% to 7.083%, total return from +218.46% to +241.70%, OOS annualized return from 10.043% to 10.695%, and beta-hedged annualized return from 7.502% to 8.004%. Corrected FDR still found 0 final statistical candidates. | Promote to simulation-observation watchlist only. |

## What Changed

The important process correction is not the factor name itself. It is the move from replacement-style testing to incremental-overlay testing.

Earlier public indicators looked good in projection, then failed when rebuilt formally because they replaced part of the working base. Round441 fixed this by letting a new factor act as a second-layer tilt on top of the current delayed-exit Alpha101/Dragon baseline.

## Audit Decision

The sprint should not continue ordinary RSRS/SuperTrend-style technical overlay mining. That route produced projection false positives and poor coverage.

The next work block should prioritize:

- capacity-safe price-volume factors tested as incremental overlays;
- event-context or tradeability/liquidity microstructure only when point-in-time coverage is already available;
- strict split/bootstrap checks before any simulation-readiness claim.

Round442 is useful because it improves the current return-seeking lane, but it is not a final profitable alpha. It must survive Round443-style split/bootstrap evidence, paper handoff review, and future out-of-sample monitoring before it can replace the default.
