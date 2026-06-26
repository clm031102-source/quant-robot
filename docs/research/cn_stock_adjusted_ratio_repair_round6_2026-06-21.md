# CN Stock Adjusted-Ratio Repair Round 6

- Date: 2026-06-21
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock authority bars and same-parameter replay

## Why This Round Exists

Round 5 found mass adjusted-price ratio discontinuities on `2023-07-03` and `2025-07-01`. Those jumps created impossible trade returns and made factor evidence unreliable. Round 6 repaired only the mass discontinuity pattern at load time, then reran the same Round 4 parameters.

## Tooling Added

- Config: `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_repaired.json`
- Loader repair controls:
  - `repair_adjusted_ratio_mass_jumps`
  - `adjusted_ratio_jump_threshold`
  - `adjusted_ratio_mass_jump_asset_threshold`
- Loader repair function: `repair_adjusted_ratio_mass_jumps`

The repair is read-time only. It does not rewrite `data/processed`.

## Data Manifest Evidence

Command:

```powershell
python scripts\run_cn_stock_data_manifest.py --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_repaired.json --daily-basic-root configs\cn_stock_authority_daily_basic_inputs_2015_2025.json --market CN --output-dir data\reports\cn_stock_data_manifest_adjusted_ratio_repaired
```

Result:

- Status: `review_required`
- Blockers: none
- Bar rows: 10,759,495
- Bar symbols: 5,707
- Date range: 2015-01-05 to 2025-12-31
- Daily-basic rows: 10,700,940
- Adjusted ratio jump rows: 1,194
- Adjusted ratio jump assets: 982
- Adjusted ratio mass jump dates: 0
- Remaining warnings:
  - `extreme_return_rows_present`
  - `adjusted_ratio_jump_rows_present`
  - `moneyflow_symbol_coverage_below_bars`

Interpretation: the system-wide discontinuity is repaired, but single-name adjusted-price anomalies remain. This data is acceptable for research replay with explicit warning review, not for promotion or live use.

## Same-Parameter Replay

Command:

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621.json --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_repaired.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_repaired.json --data-manifest-packet data\reports\cn_stock_data_manifest_adjusted_ratio_repaired\cn_stock_data_manifest.json --allow-review-required-data-manifest --output-dir data\reports\experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621_adjusted_ratio_repaired
```

Result: 3 cases completed, 0 failed, 0 no-trade.

| factor | decision | total return | relative return | Sharpe | overlap-adj Sharpe | max DD | win rate | mean IC | mean RankIC | cap-limited trades | extreme flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `value_low_turnover_low_tail_20` | rejected | 2.36 | -35.41 | 0.668 | 0.345 | -41.97% | 52.02% | 0.0439 | 0.0796 | 0 | true |
| `dividend_value_liquid_low_tail_20` | rejected | 0.97 | -36.80 | 0.443 | 0.230 | -50.07% | 52.58% | 0.0183 | 0.0402 | 0 | false |
| `value_liquid_low_tail_20` | rejected | 1.26 | -36.50 | 0.455 | 0.230 | -50.79% | 49.21% | 0.0148 | 0.0350 | 0 | true |

## Residual Extreme Trade Evidence

Diagnostic command:

```powershell
python scripts\run_extreme_trade_diagnostic.py --config configs\experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621.json --factor-name value_low_turnover_low_tail_20 --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_repaired.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_repaired.json --data-manifest-packet data\reports\cn_stock_data_manifest_adjusted_ratio_repaired\cn_stock_data_manifest.json --allow-review-required-data-manifest --output-dir data\reports\extreme_trade_diagnostic_daily_basic_value_liquidity_tail_round6_repaired_20260621 --diagnostic-top-n 20
```

Result:

- Trades inspected: 52,799
- Extreme trades above 5x: 2
- Max abs gross return: 52.8563
- P99 abs gross return: 0.4132

Both residual extreme trades are `600777.SH`:

- Signal 2025-04-16, entry 2025-04-17, exit 2025-07-22, gross return 52.8563, entry `adj_close` 86.9678, exit `adj_close` 4683.7611
- Signal 2025-04-09, entry 2025-04-10, exit 2025-07-15, gross return 44.8296, entry `adj_close` 81.4751, exit `adj_close` 3733.9726

Interpretation: the remaining extreme flag is a single-name data-quality anomaly, not a broad factor signal.

## Decision

No Round 4 daily-basic value/liquidity/tail candidate is promotable. The best item, `value_low_turnover_low_tail_20`, may be kept only as a component research lead because it has positive IC and improved drawdown after data repair, but it still fails relative-return and residual data-quality gates.

Next cycle should not expand this family blindly. Use the repaired authority-bars config as the default CN stock research data root, add a single-name anomaly quarantine before promotion, and rotate the alpha search to public-method price-volume/trend-confirmed families.
