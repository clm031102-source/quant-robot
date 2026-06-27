# CN Stock Rounds443-445 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Audit the three-round block after the first useful range-contraction increment.

## Round Summary

| Round | Work | Useful Output | Decision |
|---:|---|---|---|
| 443 | CPCV and quarterly bootstrap for Round442 `range_q10_m150` | Annualized delta positive in 99.30% of bootstrap paths; CPCV annualized win rate 90.83%; bootstrap DD<=30% only 57.90%. | Good simulation-observation lead, not final alpha. |
| 444 | Test three other capacity-safe PV expressions | Bollinger and PV-corr improved return versus base but failed to beat Round442 overlap quality; amount-stability weaker. | Reject expression hopping. |
| 445 | Narrow sensitivity around range-contraction top fraction and multiplier | `range_q20_m175` reached 7.723% annualized return, +280.30% total return, overlap 0.512, max DD -29.31%; OOS annualized 11.739%. | Add aggressive observation lane; keep cost-robust default separate. |

## Direction Check

This block did not repeat the earlier mistake of endlessly mining one weak family. It tested whether the first real lead is stable, then checked adjacent expressions, then performed narrow parameter sensitivity.

The answer is nuanced:

- the range-contraction increment is real enough for simulation observation;
- the broader low-vol reversal cluster is not worth blind expression expansion;
- more aggressive range settings lift return materially, but cost and drawdown fragility rise quickly.

## Active Candidates After This Audit

| Role | Candidate | Reason |
|---|---|---|
| Cost-robust range observation | `range_q10_m150` | Best balanced evidence across 10/20/30 bps stress. |
| Aggressive high-return observation | `range_q20_m175` | Strongest 10 bps full-sample and OOS candidate inside about 30% full-sample drawdown. |
| Secondary aggressive observation | `range_q10_m200` | Good 10/20 bps metrics, but inferior 30 bps stress fallback. |

## Next Direction

Stop expanding the low-volatility reversal cluster for now.

Next work should either:

- package `range_q10_m150` and `range_q20_m175` into the paper-simulation handoff/ranking flow; or
- rotate to a genuinely different point-in-time family, such as event-context underreaction, tradeability/liquidity microstructure, or audited financial/PIT factors.

Do not touch the 2026 final holdout during this sprint.
