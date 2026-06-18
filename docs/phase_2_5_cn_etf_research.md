# Phase 2.5 CN ETF Research

This phase adds A-share ETF research readiness without live trading.

It supports `CN_ETF` as a dedicated research market that shares China exchange calendars, CNY currency, and Asia/Shanghai timezone, while keeping ETF assets separate from individual A-shares.

## What Is Ready

- Tushare-first CN ETF universe policy in `configs/universe_cn_etf.yaml`.
- Point-in-time ETF pool construction from Tushare `fund_basic(market='E')`.
- Point-in-time CN_ETF rotation membership from `fund_basic` list/delist dates plus trailing bar-quality filters.
- Tushare `fund_daily` ingestion for CN_ETF daily bars.
- Tushare `etf_share_size` ingestion for ETF share, scale, NAV, and premium/discount auxiliary features.
- Tushare `fund_portfolio` ingestion into ETF-level moneyflow basket mappings.
- ETF-level moneyflow basket factors that aggregate CN stock moneyflow through point-in-time ETF constituent or theme mappings.
- Demo ETF fixture bars in the same unified market-data schema.
- TradingView ETF CSV import into local processed bars.
- Factor research, experiment grid, walk-forward validation, signal snapshots, and paper simulation with `market=CN_ETF`.
- Import safety checks for filename/symbol mismatch and a local import lock to prevent concurrent partition rewrites.
- Paper simulation rounds A-share ETF fills to 100-share lots.
- Local GUI market selection for A股 ETF.

## Tushare CN ETF Primary Pool

The primary research pool is Tushare-based:

- `fund_basic(market='E')` provides the exchange-traded fund universe.
- The project filters to listed ETFs with `.SH` or `.SZ` codes and applies `list_date` / `delist_date` when an `as_of` date is supplied.
- The sync also writes `metadata/cn_etf_rotation_membership/market=CN_ETF`, which preserves delisted or formerly listed ETFs on dates when they were listed, then excludes them from rotation after their `delist_date`. This is the research membership surface for walk-forward runs; the current tradable pool remains an as-of subset.
- Research, experiment-grid, walk-forward, signal-snapshot, and paper-simulation entrypoints keep full bars for factor warmup and data audits, then filter factor signals by `date, asset_id` against the rotation membership surface. For `processed-bars` plus `market=CN_ETF`, the CLI wrappers use `--data-root` as the default membership root and require the dataset.
- `fund_daily` provides CN_ETF daily OHLCV bars for full-history and incremental refreshes.
- `etf_share_size` provides the auxiliary ETF share, scale, NAV, and close series used to derive demand-pressure proxies such as share change and NAV premium/discount.
- `fund_portfolio` provides the default ETF-to-stock basket mapping for stock-flow aggregation. The project uses `ann_date` as `known_date`, never `end_date`, and expires each basket on the day before the next announcement for the same ETF.
- CN stock `moneyflow` is not a primary trading universe. It is admissible only after aggregation into ETF-level breadth, theme-flow, or risk-appetite features using mappings whose `known_date` is no later than the signal date.
- Static symbols, CSV, AKShare, and fixture paths are fallback or smoke-test paths only.

Run the Quant PM startup gate before any desktop data refresh:

```powershell
$env:PYTHONPATH='src'
python scripts\run_quant_pm_startup_gate.py --machine highspec_desktop --task data_pipeline --branch <current-branch>
```

Then ingest full-history or recent Tushare ETF bars:

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_family_scheduler.py --config configs\research_family_scheduler_cn_etf.json
python scripts\run_tushare_cn_etf_sync.py --source tushare --start-date auto --end-date latest --output-dir data\processed\tushare_etf_full --report-dir data\reports\tushare_cn_etf_sync --min-rotation-history-rows 60 --min-rotation-median-amount 10000000 --execute
python scripts\run_data_quality_audit.py --data-root data\processed\tushare_etf_full --market CN_ETF --output-dir data\reports\data_quality_gap_audit_cn_etf_full
```

Generated raw, processed, and report data stay out of Git.

`--start-date auto` resolves to the configured full-history anchor, currently `2005-01-01` unless overridden with `--full-history-start-date`. `--end-date latest` resolves through Tushare `trade_cal` to the most recent completed open trading day; when provider readiness is missing, the sync writes a blocked pack with `date_resolution` evidence instead of guessing a trading calendar date.

For daily refresh after the full-history root exists, use incremental mode:

```powershell
$env:PYTHONPATH='src'
python scripts\run_tushare_cn_etf_sync.py --source tushare --start-date incremental --end-date latest --output-dir data\processed\tushare_etf_full --report-dir data\reports\tushare_cn_etf_sync_incremental --min-rotation-history-rows 60 --min-rotation-median-amount 10000000 --execute
```

`--start-date incremental` reads the latest local `CN_ETF` processed bar date and starts from the next calendar day. If the local root is already current through the resolved latest completed trading day, the sync writes an `up_to_date` pack and skips downloads.

The sync writes the point-in-time rotation membership and ETF basket mapping under:

```text
data\processed\tushare_etf_full\metadata\cn_etf_rotation_membership\market=CN_ETF
data\processed\tushare_etf_full\metadata\etf_moneyflow_baskets\market=CN_ETF
```

These rows are auxiliary inputs only. They are allowed to feed ETF-level moneyflow breadth, theme-strength, and risk-appetite factors, but not direct CN stock selection.

## Import TradingView ETF CSV

Use this path only when provider credentials are unavailable or a small local smoke dataset is needed.

Export daily ETF data from TradingView, then run:

```powershell
$env:PYTHONPATH='src'
python scripts\import_etf_csv.py path\to\510300.csv --symbol 510300.SH --output-dir data\processed\etf_csv
```

Import additional ETF CSVs into the same output root. The importer merges symbols into the same `CN_ETF` year partition instead of replacing the whole ETF dataset. Run imports one at a time; the importer creates `.import_etf_csv.lock` and refuses to run if another import is already active.

Use filenames that contain the ETF code, such as `510300.csv` or `510300_1D.csv`. If the filename code conflicts with `--symbol`, the import fails instead of silently labeling the data as the wrong ETF.

For multiple TradingView exports, put the raw files in one folder and run the batch importer:

```powershell
$env:PYTHONPATH='src'
python scripts\batch_import_etf_csv.py --input-dir . --raw-dir data\raw\tradingview_etf_csv --output-dir data\processed\etf_csv --move-raw
```

The batch importer infers `.SH`/`.SZ` from TradingView filenames such as `SSE_DLY_510300, 1D_xxx.csv` and `SZSE_DLY_159915, 1D_xxx.csv`, moves them into stable project filenames like `510300_SH_1d.csv`, then writes a `batch_import_manifest.json`.

## Run ETF Research

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor momentum_20 --top-n 2 --cost-bps 5 --output-dir data\reports\research_pipeline_cn_etf
```

Run the ETF share, scale, NAV, and demand-pressure auxiliary factor source:

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor-source etf_share_size --factor-input-root data\processed\tushare_etf_full --factor share_change_1d --top-n 2 --cost-bps 5 --output-dir data\reports\research_pipeline_cn_etf_share_size
```

Run ETF-level moneyflow basket auxiliary factors only after both the CN moneyflow inputs and ETF basket mappings are available. The mapping dataset lives under `metadata/etf_moneyflow_baskets/market=CN_ETF` and must include `etf_asset_id`, `stock_asset_id`, `weight`, and `known_date`. For Tushare-derived mappings, `known_date` is the portfolio announcement date from `fund_portfolio.ann_date`.

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor-source etf_moneyflow_basket --factor-input-root data\processed\tushare_etf_full --moneyflow-input-root data\processed\tushare_moneyflow_inputs --factor etf_net_mf_amount_ratio --top-n 2 --cost-bps 5 --output-dir data\reports\research_pipeline_cn_etf_moneyflow_basket
```

## Run ETF Factor Mining Grid

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_etf.json --source processed-bars --data-root data\processed\tushare_etf_full
```

For the lower-turnover research path, run the dedicated grid. It uses longer factor windows, 5-day holding, 5/10-day rebalance intervals, and realistic transaction costs:

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_etf_low_turnover.json --source processed-bars --data-root data\processed\tushare_etf_full
```

When `periods_per_year` is left unset, the pipeline scales annualization by the rebalance interval. For example, a 5-day rebalance interval uses roughly `252 / 5` periods per year rather than pretending each return is daily.

## Run ETF Walk-Forward Validation

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_rotation.json --source processed-bars --data-root data\processed\tushare_etf_full
```

ETF structure and demand-pressure walk-forward validation:

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_share_size.json --source processed-bars --data-root data\processed\tushare_etf_full
```

ETF-level stock-flow breadth and theme-strength walk-forward validation:

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_moneyflow_basket.json --source processed-bars --data-root data\processed\tushare_etf_full
```

Lower-turnover walk-forward validation:

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --config configs\walk_forward_cn_etf_low_turnover.json --source processed-bars --data-root data\processed\tushare_etf_full
```

## Run ETF Paper Simulation

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_simulation.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor momentum_20 --top-n 2 --initial-cash 100000 --max-asset-weight 0.4 --min-cash-weight 0.1
```

## Safety Boundary

This phase still does not connect to brokers, does not read a real account, and does not place orders. Paper simulation fills are local simulated records only.

Tushare ETF daily fetching is wired through `fund_daily`, with `etf_share_size` as the ETF structure auxiliary dataset and `fund_portfolio` as the default point-in-time ETF basket source. When provider credentials are unavailable, `CN_ETF` research can still use local CSV or fixture data for smoke checks, but those are not the primary research pool for desktop factor mining.

Direct `CN` stock moneyflow selection remains out of scope for this phase. Stock moneyflow-derived outputs are valid only when they are aggregated to `CN_ETF` rows before factor evaluation, walk-forward validation, paper simulation, or signal snapshots.
