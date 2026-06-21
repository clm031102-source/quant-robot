# CN Stock Low-Turnover Capacity-Clean Replay Round85 - 2026-06-21

## Purpose

Round85 replayed the two Round83 low-turnover leads with the Round84 process fixes active.

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Frozen factors: `turnover_rate_low`, `turnover_rate_f_low`
- Data: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`
- Config: `configs/experiment_grid_cn_stock_low_turnover_capacity_clean_round85_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_low_turnover_capacity_clean_round85_20260621`

Research only. No broker connection, no account reads, no order placement, and no live-trading action.

## Process Fixes Added Before Replay

Round85 added reusable gates to the core backtest path:

- `min_signal_amount`: known-at-signal-date amount filter before TopN selection.
- `max_calendar_holding_days`: conservative execution-validity gate that skips trades whose actual entry-to-exit calendar span is too long.
- Leaderboard metrics for signal-amount filtering, calendar-limited skipped trades, and calendar-holding days.
- Decision rejection for calendar-limited trades.

These were added with TDD and verified through backtest, research-pipeline, and experiment-grid tests.

## Command

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_low_turnover_capacity_clean_round85_20260621.json --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-manifest-packet data\reports\cn_stock_data_manifest_round83_daily_basic\cn_stock_data_manifest.json --allow-review-required-data-manifest
```

Startup gate status:

- `startup_gate_cleared`: true
- blockers: none
- next direction before run: `round85_calendar_holding_liquidity_gate_replay`

## Replay Settings

| Setting | Value |
|---|---:|
| TopN | 100 |
| Cost | 10 bps |
| Market impact | 20 bps |
| Max participation | 1% ADV |
| Signal-date amount gate | 10,000,000 |
| Max calendar holding | 60 days |
| Forward horizon | 20 bars |
| Rebalance interval | 5 bars |
| Period | 2015-01-05 to 2025-12-31 |

## Round85 Results

| Factor | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Relative Return | RankIC | RankIC t | Trades | Signal Rows Filtered | Calendar-Limited | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `turnover_rate_low` | +177.86% | 6.02% | 0.755 | 0.410 | -34.63% | 53.35% | -2195.89% | 0.1028 | 13.61 | 52,791 | 546,988 | 205 | 1 | rejected |
| `turnover_rate_f_low` | +130.86% | 4.62% | 0.582 | 0.294 | -44.97% | 52.73% | -2242.88% | 0.1079 | 15.72 | 52,658 | 546,968 | 332 | 1 | rejected |

## Comparison With Round83 Raw Results

| Factor | Round83 Raw Total | Round85 Clean Total | Round83 Overlap Sharpe | Round85 Overlap Sharpe | Interpretation |
|---|---:|---:|---:|---:|---|
| `turnover_rate_low` | +5127.61% | +177.86% | 0.961 | 0.410 | return engine mostly removed by tradeability gates |
| `turnover_rate_f_low` | +5318.72% | +130.86% | 0.902 | 0.294 | return engine mostly removed by tradeability gates |

The IC did not disappear, but the tradable long-only portfolio did not survive.

## Remaining Failure Evidence

Both factors still failed hard gates:

- They underperformed the equal-weight CN stock benchmark by more than 21x total return.
- They retained one capacity-limited trade each even after signal-date amount gating.
- They still selected trades that had to be skipped by the 60-day calendar-holding gate.
- Tail IC was not significant:
  - `turnover_rate_low` tail RankIC t = 1.31
  - `turnover_rate_f_low` tail RankIC t = 0.36
- Overlap-aware t-stats were weak:
  - `turnover_rate_low` Newey-West t = 1.72
  - `turnover_rate_f_low` Newey-West t = 1.26

Remaining capacity breach:

| Factor | Asset | Signal | Entry | Exit | Signal Amount | Entry Amount | Participation | Gross Return |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_low` | `CN_XSHG_600301` | 2015-07-06 | 2015-07-07 | 2015-08-04 | 23,452,575 | 247,131 | 1.0116% ADV | -10.32% |
| `turnover_rate_f_low` | `CN_XSHG_600301` | 2015-07-06 | 2015-07-07 | 2015-08-04 | 23,452,575 | 247,131 | 1.0116% ADV | -10.32% |

## Decision

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research leads carried forward from raw low-turnover direct line: 0

Round85 confirms that raw low-turnover direct TopN should be hibernated. The signal has ranking information, but the tradable implementation is too weak and too dependent on the exact tradeability filters.

## Next Direction

Do not continue with:

- low-turnover TopN/window tuning;
- signal-amount gate as a standalone rescue;
- calendar-skip cleanup as promotion evidence;
- more daily-basic pure liquidity sweeps.

Next work should rotate to a different, publicly grounded and capacity-safe family:

`round86_capacity_safe_public_quality_value_momentum_composite`

Minimum design:

- pre-register a small set of public-anomaly composites;
- use signal-date amount/liquidity gates before selection;
- include calendar-holding gate in every replay;
- compare IC, tail IC, overlap-adjusted Sharpe, drawdown, relative return, and capacity;
- only walk forward if long-cycle replay clears hard gates.
