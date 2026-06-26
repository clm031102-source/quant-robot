# CN ETF Liquid Universe Round 25

Date: 2026-06-21

## Purpose

Round 25 turned the wide CN ETF dataset into a reusable liquid-continuous ETF universe gate.

This addresses a root cause from earlier weak factor results: broad ETF mining on raw Tushare data can select short-history, stale, illiquid, or abnormal-return instruments and create false positives.

## Implementation

New repeatable components:

- `src/quant_robot/ops/etf_liquid_universe.py`
- `scripts/run_etf_liquid_universe_filter.py`
- `tests/unit/test_etf_liquid_universe.py`

The experiment grid now supports:

- `asset_universe_path`

When set, the grid filters bars before factor precomputation and before research-pipeline execution.

## Real Run

Command:

```powershell
python scripts\run_etf_liquid_universe_filter.py --source processed-bars --data-root data\processed\tushare_etf_wide_history_2023_2026 --market CN_ETF --output-dir data\reports\etf_liquid_universe_tushare_wide_2020_2024_round25 --required-asset-id CN_ETF_XSHG_510300
```

Output packet:

- `data/reports/etf_liquid_universe_tushare_wide_2020_2024_round25/etf_liquid_universe.json`

Status:

- Cleared

## Policy

Applied thresholds:

- Minimum history days: 756
- Recent window: 60 trading dates
- Minimum recent observations: 40
- Minimum median recent amount: 5,000,000
- Maximum stale-price rate: 5%
- Extreme-return threshold: 20%
- Maximum extreme-return rate: 0.5%
- Minimum selected assets: 20
- Required benchmark asset: `CN_ETF_XSHG_510300`

## Result

Input:

- Rows: 1,119,490
- Assets: 1,781
- Date range: 2020-01-02 to 2024-06-28
- Trading dates: 1,085

Selected:

- Liquid-continuous ETF assets: 264
- Benchmark selected: yes

Rejection reason counts:

| Reason | Count |
|---|---:|
| history_days_below_minimum | 1,025 |
| recent_amount_below_minimum | 1,092 |
| recent_observations_below_minimum | 462 |
| stale_price_rate_above_limit | 644 |
| extreme_return_rate_above_limit | 16 |

The counts overlap because one ETF can fail multiple gates.

## Interpretation

This is a meaningful process upgrade, not a factor discovery.

Round 25 produced:

- New factor names: 0
- Promotable factors: 0
- Reusable mining infrastructure: 1 liquid-continuous ETF universe gate

The next ETF factor runs should use the generated `asset_universe_path` instead of the raw 1,781-ETF universe.

## Next Round

Round 26 should run a small, public-reference ETF factor grid on the filtered 264-ETF universe:

- dual momentum / relative strength,
- volatility-adjusted momentum,
- low-volatility trend,
- drawdown recovery,
- breadth or risk-on overlays.

The run must keep the same long-cycle and out-of-sample discipline:

- no same-sample parameter promotion,
- transaction costs enabled,
- walk-forward validation required before any paper-ready claim,
- every result counted, including rejected cases.
