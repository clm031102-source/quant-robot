# CN Stock Round445 Range-Contraction Sensitivity Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round445 tests a narrow parameter neighborhood around the Round442 lead `range_contraction_lowvol_reversal_20`.

Grid:

- top fraction: 5%, 10%, 15%, 20%;
- exposure multiplier: 1.25x, 1.50x, 1.75x, 2.00x;
- same delayed-exit Alpha101/Dragon base;
- same entry-timed volatility target 8%, 84-event lookback, max exposure 1.00;
- same entry-timed self-risk rule.

## Main 10 bps Result

| Candidate | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Leave-One-Year Min Ann. | OOS Ann. | OOS Strict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Base delayed-exit | 6.663% | +218.46% | 0.968 | 0.496 | -26.21% | 5.001% | 10.043% | 90.00% |
| `range_q10_m150` | 7.083% | +241.70% | 0.984 | 0.505 | -26.99% | 5.323% | 10.695% | 90.00% |
| `range_q10_m200` | 7.434% | +262.40% | 0.992 | 0.510 | -28.10% | 5.564% | 11.253% | 90.00% |
| `range_q20_m175` | 7.723% | +280.30% | 0.997 | 0.512 | -29.31% | 5.713% | 11.739% | 90.00% |
| `range_q20_m200` | 8.023% | +299.79% | 1.003 | 0.515 | -30.30% | 5.891% | n/a | n/a |

`range_q20_m200` has the highest return, but it breaches the approximate 30% drawdown line. `range_q20_m175` is the strongest 10 bps candidate that stays inside the line in full-sample metrics.

## Cost Stress

| Candidate | Cost Lane | Annualized | Total Return | Overlap Sharpe | Max DD | Decision |
|---|---|---:|---:|---:|---:|---|
| `range_q20_m175` | 20 bps VT 8% | 7.061% | +240.44% | 0.475 | -31.07% | Too aggressive for default |
| `range_q20_m175` | 20 bps VT 7.5% | 6.901% | +231.46% | 0.473 | -30.63% | Still fragile |
| `range_q20_m175` | 30 bps VT 7% | 6.057% | +187.46% | 0.428 | -32.04% | Reject stress lane |
| `range_q10_m200` | 20 bps VT 8% | 6.722% | +221.62% | 0.468 | -30.33% | Borderline |
| `range_q10_m200` | 20 bps VT 7.5% | 6.590% | +214.55% | 0.467 | -29.79% | Heavy-cost observation only |
| `range_q10_m200` | 30 bps VT 6% | 5.513% | +162.14% | 0.420 | -29.53% | Worse than existing `q10_m150` stress fallback |

The existing Round442 `range_q10_m150` remains the better cost-stress fallback: 20 bps annualized return 6.458% with max drawdown -28.87%, and 30 bps VT 7% annualized return 5.581% with max drawdown -29.97%.

## Incremental Robustness

Relative to the delayed-exit base:

| Candidate | Delta Ann. | Delta Total | Delta Overlap | CPCV Ann Win | CPCV Strict | Bootstrap Ann+ | Bootstrap Overlap+ | Bootstrap DD<=30% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `range_q10_m150` | +0.419% | +23.24% | +0.009 | 90.83% | 67.50% | 99.30% | 89.00% | 56.00% |
| `range_q20_m175` | +1.059% | +61.84% | +0.016 | 89.17% | 65.83% | 99.20% | 83.50% | 54.40% |
| `range_q10_m200` | +0.771% | +43.94% | +0.014 | 90.00% | 66.67% | 99.70% | 86.30% | 58.10% |

The parameter neighborhood is not a single spike. However, higher return comes with heavier path drawdown risk in bootstrap.

## Statistical Reality Check

Round445 ran a 17-row check across the base plus the 16 range-contraction sensitivity rows.

Result:

- FDR-significant rows: 17;
- sensitivity stable peak: true;
- best by annualized return: `range_q20_m200`;
- best within the approximate 30% full-sample drawdown line: `range_q20_m175`.

Important caveat: this check tests absolute return streams. Since the base itself is also significant, this is not proof that every row is an independent alpha. The incremental CPCV/bootstrap table above is the better promotion evidence.

## Decision

Promote `range_q20_m175` to aggressive simulation-observation watchlist, not default replacement.

Keep `range_q10_m150` as the more cost-robust range-contraction observation lane.

Keep `range_q10_m200` as a secondary 10/20 bps observation, but do not use it as the 30 bps stress fallback.

Do not continue widening this parameter grid unless a paper-simulation adapter specifically requires a high-return aggressive lane.
