# CN Stock Three-Round Review Round58-60

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Rounds Reviewed

Round58: public formula price-volume industry-neutral replay.

- Factors: 8
- Industry-neutral signal factors: 8
- Portfolio cases: 16
- Approved cases: 0
- Best clean lead: `formula_pv_corr_reversal_20`, rebalance 5
- Best total return: 35.48%
- Best Sharpe: 0.3134
- Best overlap-adjusted Sharpe: 0.1771
- Best max drawdown: -26.71%
- Best win rate: 46.87%
- Best relative return: -23.3827

Round59: IC-to-portfolio gap audit.

- Cases audited: 16
- Strong RankIC cases: 16
- IC-to-portfolio gap cases: 16
- Capacity-limited cases: 10
- Promotable long-only cases: 0
- Decision: stop raw public-formula TopN expansion

Round60: `formula_pv_corr_reversal_20` bottom-exclusion overlay.

- Rebalance 5: bottom-exclusion candidate, overlay t-stat 8.19, positive rate 68.43%
- Rebalance 10: bottom-exclusion candidate, overlay t-stat 6.42, positive rate 70.45%
- Decision: keep as risk-filter research lead, not as standalone buy factor

## What Changed

The workflow moved from blind factor-name expansion to evidence-driven translation:

- public indicators are now treated as economic hypotheses;
- strong IC must be followed by portfolio conversion audit;
- broad families are stopped when all cases fail promotion;
- a single clean lead is isolated before more expensive validation;
- three-round review is now actively changing the next direction.

## Current Best Lead

`formula_pv_corr_reversal_20` as a bottom-exclusion risk filter.

Evidence:

- strong long-cycle RankIC;
- strong industry-neutral RankIC;
- no capacity-limited trades in the best direct long-only case;
- bottom bucket underperforms persistently across rebalance 5 and 10.

Blockers:

- direct long-only portfolio is rejected;
- no costed bottom-exclusion portfolio result yet;
- no walk-forward promotion gate yet;
- no final holdout claim allowed;
- industry metadata coverage still has gaps.

## Direction Decision

Next direction: `pv_corr_reversal_costed_bottom_exclusion_portfolio_batch`.

Required next run:

- use only `formula_pv_corr_reversal_20`;
- test the bottom 20% exclusion as a portfolio risk filter;
- include cost, capacity, drawdown, relative-return, fold stability, and walk-forward evidence;
- do not add new factor formulas until this translation layer either works or fails.

## Stop-Loss

If the costed bottom-exclusion portfolio still has weak Sharpe, large drawdown, or poor fold stability, this lead should be hibernated and the next family should rotate away from public price-volume formulas.
