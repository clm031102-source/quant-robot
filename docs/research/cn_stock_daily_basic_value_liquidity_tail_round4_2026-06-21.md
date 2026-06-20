# CN Stock Daily-Basic Value/Liquidity/Tail Round 4

- Date: 2026-06-21
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock cross-sectional alpha, not ETF rotation
- Data: authority CN bars + Tushare daily-basic, 2015-01-05 to 2025-12-31
- Config: `configs/experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621`

## Candidate Family

Round 4 rotates away from standalone public technical reversal and tests a public-method-inspired value/low-risk/capacity family:

- `value_liquid_low_tail_20`
- `dividend_value_liquid_low_tail_20`
- `value_low_turnover_low_tail_20`

The family uses only current and past bars plus same-date daily-basic inputs, with execution lag 1 in the research pipeline. Signals combine inverse valuation, dividend yield, liquidity/capacity rank, low downside volatility, and range-position tail guards.

## Long-Cycle Fast Grid

- Cases: 3
- Completed: 3
- Failed/no-trade: 0
- Factor matrix rows: 32,278,485
- IC observations per factor: 528
- TopN/cost/rebalance: top100, 10 bps, rebalance every 5 bars
- Holding/execution: forward horizon 20, execution lag 1
- Capacity model: portfolio value 1,000,000, market impact 20 bps, max participation 1%

| factor | decision | total return | relative return | Sharpe | overlap-adj Sharpe | max DD | win rate | mean IC | mean RankIC | cap-limited trades | extreme trade flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `value_low_turnover_low_tail_20` | rejected | 91.71 | -95.29 | 0.468 | 0.242 | -60.79% | 51.82% | 0.0403 | 0.0767 | 0 | true |
| `dividend_value_liquid_low_tail_20` | rejected | 62.01 | -125.00 | 0.454 | 0.235 | -67.41% | 52.26% | 0.0156 | 0.0382 | 0 | true |
| `value_liquid_low_tail_20` | rejected | 58.32 | -128.68 | 0.445 | 0.228 | -73.27% | 49.11% | 0.0116 | 0.0327 | 0 | true |

All three were rejected for:

- `relative_return_below_threshold`
- `drawdown_above_limit`
- extreme trade-return contamination in the trade log

## Audit Read

This round produced useful negative evidence, not a deployable factor.

Positive:

- The direction is more economically grounded than pure moneyflow-only or pure technical reversal.
- Capacity-limited trades were zero at the tested size.
- The low-turnover value/tail variant has statistically visible IC/RankIC.

Blocking:

- Long-only portfolio evidence is weak after overlap adjustment.
- Max drawdowns are far beyond the gate.
- All candidates underperform the broad CN benchmark over the authority long cycle.
- Extreme trade-return flags mean the data/label/trade path must be audited before expanding this family.
- IC strength did not translate cleanly into tradable top-N performance, so IC alone remains blocked as promotion evidence.

## Extreme Trade Diagnostic

Round 5 added a repeatable diagnostic and reran the top Round 4 candidate:

- Diagnostic output: `data/reports/extreme_trade_diagnostic_daily_basic_value_liquidity_tail_round4_20260621`
- Factor: `value_low_turnover_low_tail_20`
- Trades inspected: 52,799
- Diagnostic top rows: 20
- Max abs gross return: 145.58
- P99 abs gross return: 0.7731

The largest rows concentrate around 2025-06 to 2025-07 and show normal `close` but impossible `adj_close` jumps:

- `000001.SZ`: entry `adj_close` about 11.8 in June 2025, exit `adj_close` 1600-1700 in July 2025
- `600016.SH`: entry `adj_close` about 4.5-4.9, exit `adj_close` 170-195
- `600064.SH`: entry `adj_close` about 7.6-7.8, exit `adj_close` 240-253

This is not alpha. It is a data-quality artifact caused by adjusted-price ratio discontinuities.

The data manifest now detects adjusted-price ratio jumps. The refreshed true CN manifest reports:

- `adjusted_ratio_jump_rows`: 7,258
- `adjusted_ratio_jump_assets`: 3,230
- `adjusted_ratio_mass_jump_dates`: `2023-07-03` with 2,952 assets, `2025-07-01` with 3,112 assets
- Critical warning: `adjusted_ratio_mass_jump_dates_present`

After this change, CN processed/authority experiment grids are blocked even with `--allow-review-required-data-manifest` until this mass adjusted-price issue is handled.

## Next Direction

Do not expand this family by topN/cost/window yet. Next work should first fix the data layer:

- separate true crash/rebound events from bad adjusted-price artifacts;
- repair or quarantine the `2023-07-03` and `2025-07-01` authority-bar adjusted-price discontinuities;
- rerun the same Round 4 parameters only after the data manifest clears this critical warning;
- only after data-quality triage, test a robust public-method family with explicit trend confirmation, such as value/quality/low-vol with SuperTrend or smart-money style price-volume confirmation;
- keep same long-cycle, cost, capacity, overlap-adjusted statistics, and no-promotion-on-IC-alone gates.
