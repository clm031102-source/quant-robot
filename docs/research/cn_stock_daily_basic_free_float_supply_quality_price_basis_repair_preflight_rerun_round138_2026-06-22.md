# CN Stock Daily-Basic Free-Float Supply Quality Price-Basis Repair Preflight Rerun Round138

- Date: 2026-06-22
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Stage: `daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun`
- Scope: same frozen Round136 candidate and parameters after forcing one backtest price basis.
- Safety: research-to-review only; no broker connection, account read, order placement, or live trading.

## Why This Round Was Needed

The two high-return daily-basic/free-float supply quality variants were not rejected because 30% drawdown is automatically unacceptable. They were rejected because Round137 found that the Round136 return stream crossed an adjusted/unadjusted price-basis boundary. The backtest engine used `adj_close`; several trades entered on an unadjusted bar and exited after the data source switched to adjusted prices, creating artificial 80x to 209x trade returns.

User risk tolerance can allow roughly 30% drawdown when the return path is clean. It cannot waive data-quality, capacity, cost, or execution gates.

## Frozen Rerun Setup

- Price basis for backtest: `close`
- Shared backtest engine changed: no
- Frozen factor: `daily_basic_free_float_supply_quality_20_strict_clean_implementation_residual`
- TopN: 100
- Holding period: 20
- Rebalance interval: 20
- Execution lag: 1
- Cost bps: 10, 20
- Portfolio values: 100,000; 500,000; 1,000,000
- Guard modes: `none`, `block_stress_rebalance_dates`
- Train end: 2024-12-31
- Test start: 2025-01-01
- Final holdout: not read

## Repair Evidence

- Bars loaded: 10,785,537
- Bars repriced to single close basis: 7,802,589
- `adjusted=True` rows before repair: 8,243,882
- `adjusted=True` rows after repair: 0
- Max abs original `adj_close / close - 1`: 10,054.6401
- Max abs repaired `adj_close / close - 1`: 0.0
- Round137 phantom-alpha trades before repair: 948
- Round138 phantom-alpha trades after repair: 0

## Result After Repair

The fifty-fold style result disappeared.

Best repaired case:

- Case: `block_stress_rebalance_dates`, cost 10 bps, capital 100,000
- Total return: 28.30%
- Annualized return: 23.28%
- Sharpe: 0.931
- Overlap-adjusted Sharpe: 1.106
- Max drawdown: -15.77%
- Win rate: 53.33%
- Test total return: 23.68%
- Test Sharpe: 2.802
- Test overlap-adjusted Sharpe: 5.242
- Capacity-limited trades: 0
- Extreme trade return count: 11
- Blocker: `extreme_trade_return_present`

The unguarded 20 bps / 1,000,000 case had total return 14.50%, annualized return 4.72%, Sharpe 0.329, overlap-adjusted Sharpe 0.280, max drawdown -31.48%, and remained blocked by low overlap Sharpe, calendar skips, extreme trades, and user-floor drawdown.

## Promotion Decision

- Walk-forward allowed candidates: 0
- Paper-ready candidates: 0
- Manual/live candidates: 0
- Promotion allowed: false

Reason:

1. Round138 is a repair preflight, not a clean walk-forward validation.
2. After repair, 0 candidates passed all hard gates.
3. The repaired result still has 156 true close-basis extreme trades across 15 assets and 9 exit dates.
4. Extreme single-name returns can dominate a TopN portfolio even when capacity-limited trade count is 0.
5. Final holdout remains unread.

## Interpretation For The Two High-Return Factors

The original high total return and annualized return were not credible promotion evidence. The main reason is not drawdown. The main reason is contamination: mixed price basis converted normal close returns into impossible adjusted returns, such as `CN_XSHE_000651` from 2025-05-30 to 2025-07-01, where close return was about -2.09% but adjusted return was reported as about +20,978.86%.

After enforcing a single close basis, the best case fell to 28.30% total return. That is no longer a dramatic alpha result; it is a research lead that is still blocked by true close extreme trades.

## Next Direction

`round139_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit`

Required before any further mining or promotion claim on this family:

- Audit the 156 true close extreme trades.
- Check whether they are tradable under A-share limit-up/down, suspension, ST, listing-age, and exchange-specific constraints.
- Measure concentration by asset, exit date, and event window.
- Decide whether the residual signal survives after excluding non-tradable or event-driven jumps.
- Only if this passes, run clean walk-forward validation with the repaired price basis.

