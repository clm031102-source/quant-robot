# CN Stock Three-Round Review Round 53 - 2026-06-21

## Scope

This review covers the translation-layer work after Round50 sync:

- Round51: bottom-exclusion overlay audit.
- Round52: costed bottom-exclusion portfolio backtest.
- Prior blocker from Round49: public formula factors had strong IC but failed as long-only TopN portfolios.

## What Worked

The process improved materially:

- stopped raw TopN expansion after rejection,
- added a reusable bottom-exclusion overlay diagnostic,
- added a vectorized costed broad-basket risk-filter backtest,
- added liquidity filtering before capacity judgment,
- tightened classification so positive relative return is not mislabeled as deployable alpha.

The best empirical lead is consistent:

- `formula_volume_contraction_reversal_20` shows the strongest bottom-tail drag and best costed relative return.
- `formula_pv_corr_reversal_20` is second.

## What Failed

No factor is promotable.

The hard failures are:

- overlap-adjusted Sharpe remains far below 0.5,
- max drawdown is worse than -50%,
- win rate is around 50%,
- absolute annualized return is weak after costs,
- broad-market drawdown risk dominates the equity curve,
- the strategy is not a standalone profitable portfolio.

`formula_range_contraction_breakout_20` should be deprioritized:

- Round51 overlay t-stat was weak,
- Round52 relative improvement was small,
- annual relative folds were only 8/11,
- drawdown was worst in the group.

## Root Cause

The factor has directional tail information, not enough standalone alpha.

This means:

- it can help avoid weak names,
- it does not solve market exposure,
- equal-weight broad baskets still ride the A-share cycle,
- excluding the bottom 20% improves relative performance but not risk-adjusted absolute performance.

The previous poor results were not only because of bad factor formulas. The bigger issue was incomplete portfolio translation:

1. Strong IC does not imply long-only TopN profitability.
2. Strong bottom-tail separation does not imply standalone equity-curve quality.
3. Relative improvement can coexist with unacceptable drawdown.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads: 2.

Keep only as risk-filter components:

1. `formula_volume_contraction_reversal_20`
2. `formula_pv_corr_reversal_20`

Hibernate:

- raw public formula TopN,
- industry-neutral public formula TopN,
- standalone bottom-exclusion broad basket,
- `formula_range_contraction_breakout_20` in this translation path.

## Direction Change

Do not spend the next round on more price-volume public-formula variants.

Round54 should rotate factor family. The next batch should use public, economically grounded families that can plausibly improve absolute risk-adjusted return:

- quality / profitability proxies from daily-basic fields,
- low-volatility and downside-volatility screens,
- liquidity and capacity-aware stability,
- smart-money style proxies only if expressible without intraday look-ahead,
- optional trend/regime protection as a separate overlay, not as tuned rescue logic.

## Updated Mining Protocol

Every new family should pass this sequence before full backtest budget:

1. Pre-register factor family, formula, direction, fields, windows, and economic reason.
2. Run long-cycle IC and quantile diagnostics.
3. Decide translation layer before TopN expansion:
   - top bucket buy list,
   - bottom bucket exclusion,
   - long-short diagnostic,
   - risk overlay only.
4. Run costed vectorized validation with liquidity floor.
5. Reject or rotate immediately if:
   - overlap-adjusted Sharpe < 0.5,
   - max drawdown worse than -50%,
   - capacity fails after liquidity floor,
   - annual relative folds are unstable,
   - the factor only improves relative return while absolute risk stays poor.

## Next Action

Round54 should start a new factor family batch:

`daily_basic_quality_lowvol_smart_money_proxy`

Constraints:

- no 2026 tuning,
- long cycle 2015-2025,
- liquidity floor enabled from the first costed test,
- no raw parameter explosion,
- classify weak relative-only findings as research leads, not candidates.
