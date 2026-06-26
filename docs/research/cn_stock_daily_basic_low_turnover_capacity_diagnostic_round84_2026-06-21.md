# CN Stock Daily-Basic Low-Turnover Capacity Diagnostic Round84 - 2026-06-21

## Purpose

Round84 froze the two Round83 low-turnover leads and audited whether their very strong long-cycle returns were tradable or mainly driven by capacity, sparse trading, and extreme single-name moves.

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Data: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
- Daily-basic inputs: `configs/cn_stock_authority_daily_basic_inputs_2015_2025.json`
- Frozen config: `configs/experiment_grid_cn_stock_tushare_daily_basic_alpha_factory_core_round83_20260621.json`
- Diagnostic output: `data/reports/extreme_trade_diagnostic_cn_stock_low_turnover_round84_20260621`

Research only. No broker connection, no account reads, no order placement, and no live-trading action.

## Tooling Added

Extended the repeatable extreme-trade diagnostic so future factor batches can inspect more than raw trade returns:

- `capacity_limited_trades`
- `max_participation_rate`
- `p99_participation_rate`
- `top_weighted_return_abs_share`
- `max_calendar_holding_days`
- `p99_calendar_holding_days`
- `capacity_limited_trades.csv`
- `top_weighted_return_trades.csv`

This matters because low-turnover factors can look profitable by selecting names that are not realistically tradable, or by converting a nominal 20-bar holding period into a multi-month calendar holding period for sparse/suspended names.

## Commands

```powershell
python scripts\run_extreme_trade_diagnostic.py --config configs\experiment_grid_cn_stock_tushare_daily_basic_alpha_factory_core_round83_20260621.json --factor-name turnover_rate_low --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-manifest-packet data\reports\cn_stock_data_manifest_round83_daily_basic\cn_stock_data_manifest.json --allow-review-required-data-manifest --output-dir data\reports\extreme_trade_diagnostic_cn_stock_low_turnover_round84_20260621\turnover_rate_low --diagnostic-top-n 30

python scripts\run_extreme_trade_diagnostic.py --config configs\experiment_grid_cn_stock_tushare_daily_basic_alpha_factory_core_round83_20260621.json --factor-name turnover_rate_f_low --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-manifest-packet data\reports\cn_stock_data_manifest_round83_daily_basic\cn_stock_data_manifest.json --allow-review-required-data-manifest --output-dir data\reports\extreme_trade_diagnostic_cn_stock_low_turnover_round84_20260621\turnover_rate_f_low --diagnostic-top-n 30
```

## Round84 Diagnostic Results

| Factor | Trades | Capacity-Limited | Extreme Trades > 5x | Max Gross Return | P99 Abs Gross | Max Participation | P99 Participation | Max Calendar Holding | P99 Calendar Holding | Top Weighted Abs Share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_low` | 46,437 | 1,437 | 19 | 574.05% | 110.42% | 166.67x ADV | 2.97% ADV | 787 days | 39 days | 0.1224% |
| `turnover_rate_f_low` | 43,202 | 1,641 | 19 | 574.05% | 124.37% | 8.80x ADV | 3.24% ADV | 787 days | 42 days | 0.1189% |

## What The Trades Show

The capacity problem is real. Examples from the diagnostic:

| Factor | Asset | Signal | Entry | Exit | Calendar Days | Entry Amount | Participation | Gross Return |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_low` | `920394.BJ` | 2022-09-09 | 2022-09-13 | 2023-05-23 | 252 | 15 | 166.67x ADV | -7.99% |
| `turnover_rate_low` | `920837.BJ` | 2022-09-09 | 2022-09-13 | 2023-06-07 | 267 | 2,359 | 1.06x ADV | -11.11% |
| `turnover_rate_f_low` | `002604.SZ` | 2020-06-02 | 2020-06-03 | 2020-07-03 | 30 | 284 | 8.80x ADV | -80.28% |
| `turnover_rate_f_low` | `920765.BJ` | 2023-06-19 | 2023-06-20 | 2023-07-27 | 37 | 576 | 4.34x ADV | -23.17% |

The top absolute weighted-return rows are mostly young/high-jump names from 2015-2017 and 2020:

- Extreme trade entry years for both factors: 2015: 7, 2016: 7, 2017: 3, 2020: 2.
- Top gross-return examples include `300708.SZ`, `300556.SZ`, `002800.SZ`, `002785.SZ`, `603392.SH`, and `300424.SZ`.
- The largest individual weighted-return contribution is small as a share of total absolute weighted trade contribution, but the trade set still contains many extreme and capacity-invalid names.

## Interpretation

Round83's headline numbers were genuinely bright:

- `turnover_rate_low`: +5127.61% total return, Sharpe 1.983, overlap-adjusted Sharpe 0.961, RankIC 0.1028.
- `turnover_rate_f_low`: +5318.72% total return, Sharpe 1.872, overlap-adjusted Sharpe 0.902, RankIC 0.1079.

Round84 shows why those cannot be promoted:

- Both factors breach the capacity gate heavily.
- Both factors contain extreme >5x trade returns.
- Both factors can turn a nominal 20-bar holding into up to 787 calendar days in sparse/suspended names.
- The already-tested capacity-aware large-market variants remove capacity issues but collapse to weak overlap Sharpe and negative benchmark-relative return.

So the correct conclusion is not "low turnover is profitable." The correct conclusion is:

> Raw low turnover is a strong but contaminated research lead. Its apparent return engine is heavily entangled with illiquidity, sparse trading, and extreme young/small-name moves. It is not paper-ready and not usable for live/manual trading.

## Decision

- Promotable factors from Round84: 0
- Paper-ready factors from Round84: 0
- Manual/live usable factors from Round84: 0
- Research leads carried forward: 0 raw low-turnover direct candidates
- Infrastructure carried forward: enhanced capacity/extreme/calendar diagnostic

The raw `turnover_rate_low` and `turnover_rate_f_low` line is hibernated for promotion. It can only be revisited after the backtest process enforces calendar-holding and liquidity-exit rules, then replays a capacity-clean version with frozen parameters.

## Next Direction

Round85 should not tune low-turnover TopN or windows. It should fix the process first:

`round85_calendar_holding_liquidity_gate_replay`

Required work:

- Add a stock-backtest diagnostic/gate for calendar holding drift versus intended holding period.
- Add or enforce a liquidity/entry-amount gate before portfolio selection, not only after trade flagging.
- Replay daily-basic low-turnover only after the gate is active.
- Include capacity-safe alternatives such as market-cap bucket rank or larger liquid universes.
- Only run walk-forward if the capacity-clean replay keeps positive overlap-adjusted Sharpe and acceptable drawdown.
