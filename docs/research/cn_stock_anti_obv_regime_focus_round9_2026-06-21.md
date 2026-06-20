# CN Stock Anti-OBV Regime Focus Round 9

- Date: 2026-06-21
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock cross-sectional alpha
- Data: repaired authority CN bars, 2015-01-05 to 2025-12-31
- Config: `configs/experiment_grid_cn_stock_anti_obv_regime_focus_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_anti_obv_regime_focus_20260621_repaired`

## Why This Round Exists

Round 8 found one weak research lead: `anti_obv_breakout_low_tail_20`. It had positive IC and no extreme-trade flag, but failed drawdown, capacity, Sharpe, and relative-return gates. Round 9 tested whether portfolio construction could rescue it.

## Grid

- Factor: `anti_obv_breakout_low_tail_20`
- Cases: 12
- TopN: 30, 50, 100
- Rebalance interval: 5, 10
- Regime filter: enabled
- Regime lookback: 60, 120
- Cost: 10 bps
- Forward horizon/execution lag: 20 / 1
- Output: 12 completed, 0 failed, 0 no-trade

## Best Rows

| case | total return | relative return | Sharpe | overlap-adj Sharpe | max DD | win rate | mean IC | mean RankIC | cap-limited trades | extreme flag | decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `top50_reb10_regime120` | 0.086 | -37.68 | 0.113 | 0.121 | -37.99% | 48.50% | 0.0368 | 0.0587 | 0 | false | rejected |
| `top100_reb10_regime120` | 0.127 | -37.64 | 0.118 | 0.117 | -32.50% | 48.63% | 0.0368 | 0.0587 | 0 | false | rejected |
| `top30_reb10_regime120` | 0.047 | -37.72 | 0.101 | 0.114 | -39.06% | 45.32% | 0.0368 | 0.0587 | 0 | false | rejected |

## Audit Read

Portfolio construction helped risk controls but did not create enough edge.

Positive:

- Regime lookback 120 and rebalance 10 removed capacity-limited trades in the best rows.
- Extreme trade flags stayed false.
- Max drawdown improved to roughly -32% to -39% in the best rows.
- IC remained positive and statistically significant in the filtered sample.

Blocking:

- Total return remained tiny versus the broad CN benchmark.
- Best overlap-adjusted Sharpe stayed near 0.12, far below the walk-forward threshold.
- Win rate remained below 49%.
- Every case failed `relative_return_below_threshold`.
- Regime lookback 60 was poor, so the result is parameter-sensitive.

## Decision

No Round 9 configuration is promotable.

`anti_obv_breakout_low_tail_20` should be demoted from standalone-factor candidate to weak component candidate only. It may be useful as a risk/overextension feature inside a broader residualized model, but it should not receive more standalone grid budget.
