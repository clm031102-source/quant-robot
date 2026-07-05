# CN Stock Round532 External Macro LPR Offline Repair Tool

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 29 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, and did not touch final holdout. It added an offline tool that can repair `external_macro_rates` LPR columns from a future validated LPR cache into a fresh processed output root.

## Round Objective

Round531 made empty LPR cache files refreshable and exposed `--lpr-cache-path`. That created a safe way to obtain validated LPR cache evidence later, but the project still needed a no-provider way to apply that cache to existing macro-rate processed rows.

Round532 objective:

- add an offline repair tool that consumes an explicit LPR cache JSON;
- write repaired `external_macro_rates` to a fresh output root;
- prevent in-place overwrite of the existing long-cycle processed root;
- optionally copy other external feeds so the repaired root can be audited with the existing coverage audit;
- keep all factor and promotion work blocked.

No review agents were created in this round because the next required review-agent checkpoint is round 30 after the Round504 baseline, due in Round533.

## Startup Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 05:07 +08:00.
- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Git status before work: clean and synchronized with origin.
- Startup context: clear, branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Implementation

Added:

- `src/quant_robot/ops/external_macro_lpr_repair.py`
- `scripts/run_external_macro_lpr_repair.py`
- `tests/unit/test_external_macro_lpr_repair.py`
- `tests/unit/test_external_macro_lpr_repair_cli.py`

Tool behavior:

- Reads source `processed/external_macro_rates` partitions from a root or `processed` child root.
- Reads a JSON LPR cache with rows containing `date`, `lpr_1y`, and `lpr_5y`.
- Requires at least one non-missing LPR row.
- Applies LPR values to macro rows by backward as-of date using the macro row `date`.
- Preserves SHIBOR, `available_date`, source metadata, and year partitioning.
- Writes repaired macro rows to a fresh `output_root`.
- Refuses `output_root` equal to the normalized source root.
- Refuses non-empty `output_root`.
- Optionally copies `external_margin_detail`, `external_hk_hold`, `external_hsgt_flow`, and `external_index_state` with `--copy-other-feeds`.
- Writes JSON and Markdown repair reports.
- Keeps `promotion_allowed=false`.

## Test-First Evidence

New failing tests were added before implementation:

- `test_repairs_lpr_columns_from_cache_into_fresh_output_root`
- `test_refuses_in_place_repair`
- `test_cli_passes_paths_and_copy_flag`

Observed red evidence:

- Core test initially failed because `quant_robot.ops.external_macro_lpr_repair` did not exist.
- CLI test initially failed because `scripts.run_external_macro_lpr_repair` did not exist.

Focused green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_external_macro_lpr_repair tests.unit.test_external_macro_lpr_repair_cli tests.unit.test_tushare_external_feed_ingest tests.unit.test_tushare_external_feed_ingest_cli tests.unit.test_external_feed_coverage_audit tests.unit.test_external_feed_coverage_audit_cli
```

Result:

- 20 tests passed.

Additional local verification:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_macro_lpr_repair.py --help
.\.venv\Scripts\python.exe -m py_compile src\quant_robot\ops\external_macro_lpr_repair.py scripts\run_external_macro_lpr_repair.py
```

The help output shows `--processed-root`, `--lpr-cache-path`, `--output-root`, `--report-dir`, and `--copy-other-feeds`; compile exited `0`.

## Usage Gate

Do not run this on the current long-cycle root until an LPR cache refresh has produced non-missing cache evidence.

After Round531's report-only LPR cache refresh gate passes, use a fresh output root:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_macro_lpr_repair.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --lpr-cache-path data\reports\round532_external_lpr_cache_refresh_<YYYYMMDD>\external_lpr_cache.json --output-root data\processed\round532_external_feeds_lpr_repaired_<YYYYMMDD> --report-dir data\reports\round532_external_macro_lpr_repair_<YYYYMMDD> --market CN --copy-other-feeds
```

Then audit the repaired root:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root data\processed\round532_external_feeds_lpr_repaired_<YYYYMMDD> --output-dir data\reports\round532_external_feed_lpr_repair_coverage_audit_<YYYYMMDD> --market CN
```

Required result before any LPR-dependent work:

- `external_macro_rates.status=pass`;
- `lpr_non_null_ratio >= 0.8`;
- `lpr_1y_non_null_rows > 0`;
- `lpr_5y_non_null_rows > 0`;
- no generated data is staged for Git.

## Decision

Round532 adds source-maintenance tooling only.

It does not create non-missing LPR evidence by itself, does not repair the current long-cycle root in place, and does not allow LPR factor testing. Round533 is the next required two-agent review checkpoint and should review whether the project should prioritize quota-pack collection, LPR cache refresh, offline repair, or a new HK-hold candidate-plan gate.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run external-feed portfolio grids or promotion gates from coverage audit, join smoke, or repair reports.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
