# CN Stock Round424 - Cohort Heavy-Cost Risk Budget Grid

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round424 searches for lower-risk cohort-level variants that remain inside the user's -30% drawdown tolerance under heavier 20/30 bps equivalent cost assumptions.

This follows Round423, where the current 10 bps cohort candidate stayed inside -30%, but the same parameters breached the drawdown limit at 20/30 bps.

## Grid

Costs:

- 20 bps equivalent cost rate: `0.002`
- 30 bps equivalent cost rate: `0.003`

Overlay grid:

- target annual vol: 4%, 5%, 6%, 7%, 8%
- max exposure: 0.75, 0.85, 1.00
- self-risk window: 21, 42 closed cohort returns
- self-risk exposure: 0.50, 0.65, 0.80

Candidates tested: 180

Candidates passing the drawdown gate: 44

## Best 20 bps Variant

`cost20_cohort_openclose_vt07_max1p0_sr21_x0p8`

| Metric | Value |
|---|---:|
| total return | +134.62% |
| annualized return | 5.05% |
| Sharpe | 0.788 |
| overlap Sharpe | 0.423 |
| max drawdown | -29.96% |
| leave-one-year min annualized return | 3.11% |
| best-month log share | 53.60% |
| mean OOS annualized return | 7.42% |
| OOS strict pass rate | 90.00% |
| beta-hedged annualized return | 5.42% |
| beta-hedged max drawdown | -15.24% |

## Best 30 bps Variant

`cost30_cohort_openclose_vt07_max0p85_sr21_x0p8`

| Metric | Value |
|---|---:|
| total return | +104.87% |
| annualized return | 4.23% |
| Sharpe | 0.727 |
| overlap Sharpe | 0.387 |
| max drawdown | -28.89% |
| leave-one-year min annualized return | 2.23% |
| best-month log share | 59.54% |
| mean OOS annualized return | 5.80% |
| OOS strict pass rate | 76.67% |
| beta-hedged annualized return | 4.49% |
| beta-hedged max drawdown | -13.81% |

## Decision

If the paper simulator starts at 10 bps, keep the Round421 cohort candidate as the default.

If the simulator assumes 20 bps, use `cost20_cohort_openclose_vt07_max1p0_sr21_x0p8` as the heavy-cost comparison candidate.

If the simulator assumes 30 bps, use `cost30_cohort_openclose_vt07_max0p85_sr21_x0p8` only as a defensive stress fallback. It is profitable and within drawdown tolerance, but its best-month concentration is too close to the 60% gate to treat as a primary candidate.
