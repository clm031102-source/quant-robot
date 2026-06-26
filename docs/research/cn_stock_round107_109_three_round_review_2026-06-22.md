# CN Stock Rounds107-109 Three-Round Review - 2026-06-22

## Current Mandate

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha research
- Not scope: ETF rotation, broker connection, account reads, orders, or live trading
- Governance: review every 3 factor-family rounds, package/sync every 10 rounds when policy allows it

## Headline Result

Rounds107-109 produced no promotable factor and no paper-ready factor.

The useful output is a tighter rejection map:

- Round107 found 1 statistical research lead from the anti-overheat inverse trend/amount family.
- Round108 rejected that lead for hard redundancy against existing price-volume candidates.
- Round109 rotated to a public overnight/intraday gap family and found 0 research leads.
- The next direction must rotate again and test a more orthogonal public source: market-residual risk premia.

## Round Outcomes

| Round | Work | Main data | Result | Promotable |
|---:|---|---|---|---:|
| 107 | Negative-IC trend accumulation prescreen | 10 candidates, 20 tests, 198,871,948 aligned rows | 20 FDR-significant tests, 1 research lead | 0 |
| 108 | Dedup/capacity audit of the sole Round107 lead | 393,694 top-quantile rows, 29 reference candidates | capacity clean, but hard redundant | 0 |
| 109 | Overnight/intraday gap public family prescreen | 10 candidates, 20 tests, 201,128,582 aligned rows | 13 FDR-significant tests, 0 research leads | 0 |

## Best Signals In This Window

| Signal | Bright metric | Why it is not promoted |
|---|---:|---|
| `overheat_avoidance_relative_strength_60`, horizon 20 | IC 0.0417, ICIR 0.309, t-stat 15.75, IC>0 60.9%, Q5-Q1 0.0519 | Round108 found hard redundancy: max abs corr 0.8656 with `price_volume_trend_quality_20_60` and 0.8649 with `skip5_momentum_lowvol_20` |
| `overheat_avoidance_composite_20_60`, horizon 20 | IC 0.0637, ICIR 0.477 | monotonicity only 0.100, so the ranking shape is not portfolio-safe |
| `gap_up_intraday_fade_10`, horizon 20 | IC -0.0253, t-stat -8.60, FDR-significant | inverse direction would still have ICIR only about 0.167, below the 0.30 research threshold |
| `gap_extreme_avoidance_20`, horizon 20 | Q5-Q1 0.0624, monotonicity 0.900 | mean IC only 0.0148, below the 0.02 minimum |

## Why Good-Looking Numbers Still Failed

The user's drawdown tolerance is now explicitly encoded: a drawdown near 30 percent can be acceptable when total return, annual return, Sharpe, win rate, and long-cycle evidence are strong. That does not waive hard gates.

The blockers in this three-round window were not simple discomfort with drawdown:

- `overheat_avoidance_relative_strength_60` failed because it is not independent enough.
- `gap_up_intraday_fade_10` failed because direction stability is weak after inversion.
- `gap_extreme_avoidance_20` failed because IC is below the minimum.
- FDR significance alone was not treated as alpha, because repeated mining creates multiple-testing risk.
- No candidate reached costed walk-forward, capacity, regime, and redundancy standards.

## Work-To-Date Rollup

Recent useful achievements before this review:

| Block | Useful work product | Important number | Current status |
|---|---|---:|---|
| R91-R95 financial data path | Tushare `fina_indicator` PIT-ready shard pipeline | full100 shard had 4,328 final rows, 0 duplicate keys, 0 missing asset ids, PIT 4,412/4,412 | data capability retained |
| R96-R99 profitability quality | 14 preregistered financial factors and controlled IC screen | 28 tests, 1,204 IC observations, Bonferroni 0, FDR 0 | family hibernated |
| R101-R103 price-volume low-vol reversal | 1 long-cycle statistical lead | `bollinger_reversal_lowvol_liquid_20` IC 0.0379, ICIR 0.314, t 16.15 | hard redundant cluster, not promoted |
| R104-R106 trend/amount direction | positive trend thesis rejected; inverse thesis preregistered | `money_pressure_efficiency_20` IC -0.0952, ICIR -0.709, t -36.36 | useful as hypothesis evidence only |
| R107-R109 current window | anti-overheat lead audited; gap family tested | 40 prescreen tests plus 1 lead dedup audit | no promotion |

Older near-misses remain research memory, not usable factors:

- ETF range-contraction short-window Sharpe around 1.83 later collapsed in long-cycle replay to roughly 0.44-0.53.
- `mf_low_minus_volatility_20` showed strong relative return in a stock line but failed capacity with extreme ADV participation.
- `large_minus_liquidity_20` had attractive relative-return breadth but persistent capacity failure.
- Raw low-turnover / low-market-cap lines produced high paper returns but were capacity-constrained and drawdown-heavy.

## Audit Judgment

The repeated failure pattern is now clear: many candidates are variations of price, volume, liquidity, or hidden market exposure. They can create high IC, high Sharpe, or high relative return in narrow views, but they often fail once tested for independence, capacity, monotonicity, or out-of-sample robustness.

The next useful work should not be more same-family tuning.

## Direction Decision

Next direction:

```text
round110_market_residual_risk_premia_preregistration
```

Round110 should pre-register a public-reference family that first decomposes stock returns against an equal-weight CN stock market proxy, then tests residual and risk-premia signals:

- low market beta,
- low downside beta,
- low idiosyncratic volatility,
- residual reversal,
- residual momentum,
- low market correlation,
- crash-resilience score,
- beta-adjusted range contraction.

Required rules:

- Build the market proxy only from information available through the signal date.
- Use 2015-01-01 to 2025-12-31 long-cycle data.
- Do not touch the 2026 final holdout.
- Run IC, ICIR, t-stat, quantile monotonicity, turnover, capacity, and redundancy gates before any top-N portfolio grid.
- Treat 30 percent drawdown tolerance as a soft preference only after hard gates pass.

## Conclusion

This window produced 0 usable factors, but it did improve the mining process. The office desktop should now rotate away from anti-overheat price-volume variants and OHLC gap variants, and begin Round110 with market-residual risk premia. The goal is to separate real alpha from hidden beta before spending more compute on portfolio grids.
