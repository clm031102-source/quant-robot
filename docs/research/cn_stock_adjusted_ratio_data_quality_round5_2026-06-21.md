# CN Stock Adjusted-Ratio Data Quality Round 5

- Date: 2026-06-21
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock authority bars

## Why This Round Exists

Round 4 found positive IC in a value/liquidity/tail daily-basic family, but every candidate had `extreme_trade_return_flag=true`. Continuing to mine new factors before locating those extreme trades would waste compute and create false positives.

## Tooling Added

Added a repeatable extreme-trade diagnostic:

- `src/quant_robot/ops/extreme_trade_diagnostic.py`
- `scripts/run_extreme_trade_diagnostic.py`
- `tests/unit/test_extreme_trade_diagnostic.py`
- `tests/unit/test_extreme_trade_diagnostic_cli.py`

The diagnostic reruns one configured candidate, inspects the produced trade log, and writes:

- `extreme_trade_diagnostic.json`
- `extreme_trade_diagnostic.csv`
- `extreme_trade_diagnostic.md`

It reports asset, symbol, signal date, entry date, exit date, gross return, entry adjusted close, exit adjusted close, and source.

## Evidence

Diagnostic run:

```powershell
python scripts\run_extreme_trade_diagnostic.py --config configs\experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621.json --factor-name value_low_turnover_low_tail_20 --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025.json --allow-review-required-data-manifest --output-dir data\reports\extreme_trade_diagnostic_daily_basic_value_liquidity_tail_round4_20260621 --diagnostic-top-n 20
```

Result:

- Trades inspected: 52,799
- Diagnostic rows written: 20
- Max abs gross return: 145.58
- P99 abs gross return: 0.7731

The extreme rows were concentrated in 2025-06 to 2025-07. Examples:

- `000001.SZ`: normal close around 12, but July 2025 `adj_close` around 1600-1700
- `600016.SH`: normal close around 5, but July 2025 `adj_close` around 180-195
- `600064.SH`: normal close around 8, but July 2025 `adj_close` around 240-253

## Data Gate Added

Added adjusted-price ratio checks to the CN data manifest:

- Detects jumps in `adj_close / close`.
- Records ordinary single-name jumps as `adjusted_ratio_jump_rows_present`.
- Records mass same-day jumps as `adjusted_ratio_mass_jump_dates_present`.
- Treats mass jump dates as critical, so experiment grids cannot continue even with reviewed warnings.

True authority manifest after refresh:

- `adjusted_ratio_jump_rows`: 7,258
- `adjusted_ratio_jump_assets`: 3,230
- `adjusted_ratio_mass_jump_dates`:
  - `2023-07-03`: 2,952 assets
  - `2025-07-01`: 3,112 assets

Verification:

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_daily_basic_value_liquidity_tail_fast_20260621.json --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025.json --allow-review-required-data-manifest
```

Expected result: blocked before loading bars with critical warning `adjusted_ratio_mass_jump_dates_present`.

## Decision

No further CN stock factor mining should run on this authority-bar set until adjusted-price discontinuities are repaired or quarantined. Round 4 factors remain rejected and should not be promoted. The next productive step is data repair or a temporary quarantine protocol, followed by same-parameter replay of Round 4 before any new family expansion.
