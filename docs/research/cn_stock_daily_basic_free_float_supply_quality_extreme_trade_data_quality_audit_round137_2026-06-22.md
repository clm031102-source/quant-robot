# CN Stock Daily-Basic Free-Float Supply Quality Extreme Trade Data-Quality Audit Round137

## Scope

- Machine/task: office desktop CN stock factor validation.
- Source round: Round136 strict-clean stress-guard preflight.
- Source factor: `daily_basic_free_float_supply_quality_20_strict_clean_implementation_residual`.
- Purpose: explain the Round136 extreme-trade blocker before any walk-forward or promotion claim.
- Final holdout: not included. Window remains `2015-01-01` through `2025-12-31`.

## Result

Round137 confirms that the impressive Round136 return profile is contaminated by mixed price bases.

| Metric | Value |
|---|---:|
| Extreme trades audited | 1104 |
| Unique extreme assets | 92 |
| Unique exit dates | 11 |
| Dominant exit date | 2025-07-01 |
| Dominant trade window | 2025-05-30 -> 2025-07-01 |
| Mixed price-basis trades | 948 |
| Phantom-alpha trades | 948 |
| True close-extreme trades | 156 |
| Unexplained adjusted-return trades | 0 |
| Market-wide transition dates | 4 |
| Promotion allowed | 0 |

## Key Evidence

The leading extreme trades entered on an unadjusted close basis and exited on an adjusted basis.

| Asset | Entry | Exit | Entry adjusted | Exit adjusted | Ratio jump | Close return | Adjusted return | Class |
|---|---|---|---|---|---:|---:|---:|---|
| `CN_XSHE_000651` | 2025-05-30 | 2025-07-01 | false | true | 215.29x | -2.09% | +20978.86% | mixed price-basis phantom alpha |
| `CN_XSHG_600887` | 2025-05-30 | 2025-07-01 | false | true | 89.44x | -8.68% | +8067.59% | mixed price-basis phantom alpha |
| `CN_XSHG_600089` | 2025-05-30 | 2025-07-01 | false | true | 56.05x | +2.67% | +5654.94% | mixed price-basis phantom alpha |

The daily basis audit finds large market-wide basis transitions on `2023-07-03`, `2023-07-05`, `2023-07-12`, and `2025-07-01`. The most damaging one for Round136 is `2025-07-01`, where 5404 CN stock rows switch to adjusted prices and the median `adj_close / close` ratio jumps to about `2.4075`.

## Interpretation

The Round136 high total return and high annualized return are not reliable alpha evidence. A drawdown tolerance near 30% can be acceptable for a real strategy, but it does not waive data-quality gates. Here the core failure is not drawdown; it is return construction across inconsistent price bases.

The strict conclusion is:

- `daily_basic_free_float_supply_quality_20_strict_clean_implementation_residual` remains a research idea only.
- Round136 cannot route to walk-forward validation.
- The same frozen parameters must be rerun after enforcing a single price basis.
- No new daily-basic free-float supply quality sweeps should be started before this repair-rerun proves whether any clean return remains.

## Next Direction

`round138_daily_basic_free_float_supply_quality_price_basis_repair_and_clean_preflight_rerun`

Required next actions:

- Repair or filter mixed adjusted/unadjusted bars before portfolio backtests.
- Rerun Round136 parameters unchanged after the repair.
- Treat the remaining 156 true close-extreme trades as a liquidity/limit/stale-price audit queue.
- Keep promotion blocked until cost, capacity, walk-forward, regime, and final-holdout gates can run on clean returns.

## Artifacts

- JSON: `data/reports/daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_round137_20260622/daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit.json`
- Markdown: `data/reports/daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_round137_20260622/daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit.md`
- Asset-path CSV: `data/reports/daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_round137_20260622/daily_basic_free_float_supply_quality_extreme_trade_asset_path_audit.csv`
- Date-basis CSV: `data/reports/daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_round137_20260622/daily_basic_free_float_supply_quality_extreme_trade_date_basis_audit.csv`
