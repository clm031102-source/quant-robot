# CN Stock Round135-137 Three-Round Review

## Scope

This review closes the daily-basic free-float supply quality line from Round135 through Round137.

| Round | Work | Outcome |
|---|---|---|
| Round135 | Review Round132-134 daily-basic evidence | Allowed one strict-clean residual preflight only; no parameter expansion |
| Round136 | Strict-clean stress-guard portfolio preflight | 12 cases, 0 walk-forward candidates, blocked by extreme trades |
| Round137 | Extreme-trade data-quality audit | Root cause confirmed: mixed adjusted/unadjusted price basis creates phantom alpha |

## What Looked Good Before Audit

Round136 produced superficially attractive portfolio numbers on the frozen factor:

- Factor: `daily_basic_free_float_supply_quality_20_strict_clean_implementation_residual`
- Signal rows: 110813
- Signal dates: 31
- Best stress-guard case at 10 bps / 100k: total return about `1212.90%`, annualized return about `914.87%`, Sharpe about `1.015`, max drawdown about `-10.76%`
- OOS total return about `1163.96%`

Those numbers were not accepted because every case was blocked by extreme-trade diagnostics.

## Round137 Root Cause

Round137 audited all 1104 Round136 extreme trades:

- 948 trades are mixed price-basis phantom alpha.
- 156 trades remain true close-extreme returns and require liquidity/limit/stale-price audit.
- Dominant exit date: `2025-07-01`.
- Dominant window: `2025-05-30 -> 2025-07-01`.
- `CN_XSHE_000651` shows the failure clearly: close return was `-2.09%`, while adjusted return was `+20978.86%` because the trade crossed from unadjusted to adjusted price basis.

The conclusion is harsh but useful: the most eye-catching return data from Round136 is not evidence of a profitable factor.

## Decisions

- Promotion count remains `0`.
- Walk-forward count remains `0`.
- The daily-basic free-float supply quality line is not dead, but it is blocked until price basis is repaired.
- Drawdown tolerance near 30% remains valid as a user risk preference, but it cannot override data quality, capacity, cost, or extreme-trade gates.
- No new sweeps in this family should start before the same frozen Round136 parameters are rerun on a consistent price basis.

## Next Direction

`round138_daily_basic_free_float_supply_quality_price_basis_repair_and_clean_preflight_rerun`

Round138 must:

- Enforce one price basis for entry, exit, labels, and backtest returns.
- Rerun Round136 parameters unchanged.
- Compare the repaired result against the contaminated Round136 result.
- Audit the 156 true close-extreme trades after mixed-basis phantom trades are removed.
- Only then decide whether the family earns another walk-forward validation attempt or should hibernate.

## Anti-Waste Rule Added

Do not spend more compute on this family just because Round136 headline total return was high. The only valid reason to continue is to test whether any return survives after price-basis repair.
