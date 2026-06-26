# CN Stock Round138-140 Three-Round Review

Date: 2026-06-22

Scope:

- Round138: price-basis repair preflight rerun.
- Round139: true-close extreme trade liquidity/limit audit.
- Round140: event-adjusted clean rerun.

## Summary

This three-round block turned a contaminated high-return candidate into a cleaner, still-not-promotable research lead.

The important change is that the line is no longer being judged from a dirty 50x-style result or from repeated extreme trade rows. The current evidence is now:

- Consistent close-price backtest basis.
- Zero phantom-alpha trades.
- Round139 event paths removed before portfolio construction.
- Zero true-close extreme trades after event adjustment.
- Six clean preflight walk-forward candidates, all stress-guard dependent.

## Round-Level Results

| Round | Action | Result | Promotion |
|---|---|---|---:|
| 138 | Forced same frozen candidate onto one close-price basis | Phantom alpha removed, but 156 true-close extreme trade rows remained | 0 |
| 139 | Deduped and audited true-close extreme trades | 156 rows became 15 unique paths; 11 no-obvious paths and 4 blocked paths | 0 |
| 140 | Removed all 15 audited event paths and reran frozen grid | 0 extreme trades remained; 6 stress-guard candidates survived | 0 |

## Strongest Evidence

Round140 best clean preflight case:

- Total return: 21.31%.
- Annualized return: 18.99%.
- Sharpe: 0.820.
- Overlap-adjusted Sharpe: 1.043.
- Max drawdown: -16.37%.
- Win rate: 50.00%.
- OOS/test total return: 18.99%.
- OOS/test Sharpe: 2.913.
- OOS/test overlap-adjusted Sharpe: 5.165.
- OOS/test max drawdown: -1.62%.
- OOS/test win rate: 83.33%.
- Extreme trade count: 0.

## What Improved

- The adjusted/unadjusted price-basis bug is no longer driving the result.
- Extreme-event dependency was directly stress-tested by removing all audited event paths.
- The high-return claim became smaller but cleaner: from suspicious extreme-trade-driven results to a 18-19% annualized stress-guard preflight lead.
- Cost/capital sensitivity across 100k, 500k, and 1m remained stable for the allowed stress-guard cases.

## What Still Blocks Promotion

- The current lead is stress-guard dependent.
- Round140 is still a preflight, not full rolling walk-forward validation.
- The OOS/test window is encouraging but too short to call robust by itself.
- Final holdout remains unread.
- The event exclusion is fixed now; it must not be tuned after seeing results.

## Decision

Do not promote yet.

Continue with exactly one direction:

`round141_daily_basic_free_float_supply_quality_clean_walk_forward_after_event_adjustment`

Stop-loss rule:

If Round141 fails accepted fold count, regime coverage, or stress-guard ex-ante audit, hibernate this daily-basic free-float supply quality line and rotate family.

