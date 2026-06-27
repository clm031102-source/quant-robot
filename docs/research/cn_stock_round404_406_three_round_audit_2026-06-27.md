# CN Stock Rounds 404-406 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Decision

This three-round block was useful and directionally correct.

It rotated away from further Qlib parameter expansion and tested a broader public-factor family against the current best Dragon-Hot event lane. It produced two new simulation observations:

- an aggressive high-return Alpha101 open-close tilt;
- a balanced Alpha101 open-close cash filter with stronger drawdown and beta-hedged quality.

## Round Summary

| Round | Work | Result | Decision |
|---|---|---|---|
| 404 | Rebuilt public-factor source as target-level materialization | 32 factors, 846,400 target rows; fixed memory design | Use target-level source for selected-entry projections |
| 405 | Tested top/bottom 10% public-factor cash filters and 1.50x tilts | Alpha101 open-close/vwap/intraday families were best; sparse trend-volume lines blocked | Advance best cash and tilt candidates to wrapper audit |
| 406 | Applied vt6/ZZ500 wrapper, OOS, block, and beta audits | 13 candidates audited, 0 block failures, 90% strict OOS pass for key lanes | Add two shortlist observations |

## Best New Data

Aggressive:

- `tilt_a101_open_close_bottom10_m150_vt6_zz500_mult_1.00`
- annualized return: 7.21%
- total return: +216.69%
- overlap Sharpe: 0.558
- max drawdown: -29.84%
- OOS mean annualized return: 8.82%
- OOS worst drawdown: -24.58%
- beta-hedged annualized return: 7.18%
- beta-hedged max drawdown: -14.05%

Balanced:

- `cash_a101_open_close_top10_vt6_zz500_mult_0.75`
- annualized return: 6.10%
- total return: +166.31%
- overlap Sharpe: 0.607
- max drawdown: -22.07%
- OOS mean annualized return: 7.10%
- OOS worst drawdown: -16.68%
- beta-hedged overlap Sharpe: 0.998
- beta-hedged max drawdown: -11.27%

Reference:

- `dragon_hot_100` annualized return: 6.45%
- overlap Sharpe: 0.532
- max drawdown: -28.57%
- OOS mean annualized return: 8.02%
- beta-hedged overlap Sharpe: 0.843

## Audit

Why this did not repeat the earlier blind-mining failure:

- It used a frozen event lane and target trade universe.
- Public indicators were tested as entry filters/tilts, not standalone magic factors.
- The wrapper reused existing Round384 vt6/ZZ500 schema.
- OOS, block dependence, beta exposure, and final-holdout boundaries were checked.
- Sparse Supertrend/Smart-money/OBV signals were blocked instead of promoted.

Remaining risk:

- Alpha101 open-close signals may still be close relatives of Qlib/open-close pressure effects, so simulation should compare marginal value against Qlib self-risk rather than treat them as fully independent.
- The aggressive tilt is close to the 30% drawdown tolerance.
- No 2026 final holdout was touched.

## Next Direction

Prioritize simulation shortlist preparation and cross-candidate comparison:

- compare Alpha101 aggressive tilt, Alpha101 balanced cash filter, Qlib self-risk, and Dragon-Hot self-risk on the same paper/simulation harness;
- run correlation/overlap attribution between Alpha101 open-close and Qlib self-risk lanes;
- only then decide whether to keep mining this public Alpha101 subfamily or rotate to another independent event/accounting source.
