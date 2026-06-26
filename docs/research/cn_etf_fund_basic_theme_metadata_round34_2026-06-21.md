# CN ETF Fund Basic Theme Metadata Round34

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Objective

Prepare ETF-specific theme metadata so the next factor-mining round can test theme breadth and theme strength, rather than relying only on single-ETF price/volume formulas.

## Implementation

Added repeatable Tushare fund metadata support:

- `map_tushare_fund_basic` in `src/quant_robot/data/sources/tushare_mapping.py`
- `TushareAdapter.fetch_fund_basic` in `src/quant_robot/data/adapters/tushare_adapter.py`
- `scripts/ingest_tushare_fund_basic.py`
- Unit tests for mapping, adapter, and DatasetStore ingest path

Verification:

- `python -m unittest tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_fund_basic_ingest`
- Result: 25 tests OK

## Local Metadata Snapshot

Command executed locally:

`python scripts\ingest_tushare_fund_basic.py --source tushare --market E --output-dir data\processed\tushare_etf_wide_history_2023_2026 --snapshot 2026-06-21`

Result:

- Dataset: `metadata/tushare_fund_basic`
- Market: `E`
- Snapshot: `2026-06-21`
- Rows: 2814
- Local path: `data/processed/tushare_etf_wide_history_2023_2026/metadata/tushare_fund_basic/market=E/snapshot=2026-06-21/part-00000.parquet`

This generated data stays local and must not be committed to Git.

## Theme Map Coverage

Loaded through `load_cn_etf_theme_map(data/processed/tushare_etf_wide_history_2023_2026)`.

- Theme map rows: 1766
- Theme count: 18
- Liquid universe assets: 264
- Covered liquid-universe assets: 252
- Missing liquid-universe assets: 12

Top themes by count:

| Theme | Count |
|---|---:|
| `other_equity` | 297 |
| `broad_market` | 243 |
| `cross_border_hk` | 210 |
| `thematic_ai_digital` | 133 |
| `bond_cash` | 123 |
| `thematic_new_energy` | 94 |
| `sector_energy_materials` | 88 |
| `size_style` | 86 |
| `dividend_value` | 76 |
| `sector_healthcare` | 72 |
| `sector_consumer` | 70 |
| `sector_financial` | 65 |

## Decision

Round35 can run ETF theme-breadth validation on the same liquid CN ETF universe.

Risk:

- 12 selected ETFs lack theme mapping and will be excluded from theme-breadth factor computation.
- The theme classifier is keyword-based, so broad categories are useful for research but not yet a point-in-time commercial taxonomy.

Next:

- Run a constrained theme-breadth walk-forward grid.
- If a theme signal appears, test whether it complements `formula_range_contraction_breakout_20`.
