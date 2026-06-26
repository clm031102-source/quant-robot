# CN Stock Turnover Repair Champion Portfolio Conversion - Round126

- Date: 2026-06-22
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Stage: turnover_repair_champion_portfolio_conversion
- Factor: `turnover_rate_f_low_participation_budget_100k_20`
- Source: `docs/research/cn_stock_turnover_repair_dedup_sensitivity_round125_2026-06-22.md`
- Full output: `data/reports/turnover_repair_champion_portfolio_conversion_round126_20260622`
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Frozen Test

Round126 converted the single Round125 champion into a costed TopN portfolio audit. This was not a broad parameter search.

- Universe: CN stocks
- Data window: 2015-01-01 through 2025-12-31
- Final holdout: excluded
- Factor rows before sparse rebalance sampling: 10,127,206
- Signal rows after 20-day rebalance sampling: 504,989
- Unique assets in factor matrix: 5,701
- TopN: 100
- Holding period: 20 trading days
- Rebalance interval: 20 trading days
- Execution lag: 1
- Annualization: 252 / 20 = 12.6 periods per year
- Cost bps: 10, 20, 30
- Portfolio values: 100k, 500k, 1m, 5m
- Market impact bps: 10
- Max participation rate: 1% ADV
- User drawdown floor represented as: -40%

## Result

All 12 cost/capital cases were rejected.

- Walk-forward allowed candidates: 0
- Promotion allowed: 0
- Best total return: 1094.25%
- Best annualized return: 11.90%
- Best Sharpe: 0.224
- Best overlap-adjusted Sharpe: 0.226
- Best Newey-West t-stat on mean return: 1.061
- Win rate range: 52.5% to 55.8%
- Max drawdown range: -69.55% to -79.82%
- Extreme trade return rate: 1.61%
- Max absolute gross trade return: 205.39
- Calendar holding-gate filtered trades: 126 per case
- Capacity-limited trades: 0 at 100k/500k/1m, 12 at 5m

## Interpretation

The raw headline return is not enough. The conversion failed because the realized portfolio path is weak and fragile after overlap-aware accounting, with a drawdown far beyond the user's stated 30% tolerance and extreme trade diagnostics that are too large to ignore.

The strongest-looking case still has only 0.226 overlap-adjusted Sharpe and a -69.55% max drawdown. The 5m cases additionally breach the participation gate. The 205x max absolute gross trade return indicates that data-quality, suspension/relisting, adjustment, or extreme microstructure artifacts may be contributing to the apparent total return.

## Decision

Do not promote this factor.

Do not send it to walk-forward validation.

Hibernate the low-turnover repair family unless a new, nonredundant economic thesis appears. Future work must not continue low-turnover repair parameter tuning just because full-period total return is high.

## Next Direction

Round127 should rotate away from low-turnover repair and preregister a new public-reference, multi-family CN stock alpha batch. It should emphasize known, interpretable indicators and composites, while keeping the same gates:

- point-in-time or lag-safe inputs
- full-sample long-cycle replay
- cost and capacity stress
- overlap-aware statistics
- extreme-trade diagnostics
- regime coverage before promotion
- no final holdout read before OOS clearance

