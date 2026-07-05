# CN Stock Round533 Two-Agent Source Tooling Review

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 30 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, and did not touch final holdout. It completed the required two-agent review checkpoint and hardened LPR/source-tooling guardrails.

## Round Objective

Round532 added an offline LPR macro repair tool. Because Round533 is the round-30 checkpoint after the Round504 baseline, the objective was to pause execution and collect two independent reviews before any provider or factor action:

- Quant PM review of source/factor direction and go/no-go.
- Ordinary-user review of operator safety and misuse risk.

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

## Review Agents

Quant PM reviewer: `Hubble`

Findings:

- Analyst April cache is no-go because provider budget was exhausted in the latest same-day dry-run and required quota packs from `highspec_desktop` and `laptop` are still missing.
- Frozen January-April analyst prescreen remains a one-shot source check only after April cache succeeds; if zero leads remain, rotate.
- External-feed family hibernation remains valid: HK-hold coverage and join-smoke success are source/tooling evidence, not IC or portfolio evidence.
- LPR path remains source maintenance only until non-missing cache evidence, repaired fresh root, and passing coverage audit exist.
- Guardrail gaps before operator use: blocked repair CLI returned `0`, LPR cache checks did not require numeric plausible values, and nested output roots under source root were not explicitly rejected.

Ordinary-user reviewer: `Dirac`

Findings:

- Round533 review work should not inherit provider-enabled `factor_batch` habits blindly.
- `report-only` ingest can still call Tushare when source data or LPR cache refresh is needed; CLI help did not make that obvious.
- Offline repair CLI help was too sparse about fresh output roots, provider safety, and Git/data boundaries.
- Placeholder commands were understandable but easy to copy with `<YYYYMMDD>` still present.
- A decision table and preflight variable pattern would make the next steps safer.

## Guardrail Hardening

Changed:

- `scripts/run_external_macro_lpr_repair.py`
- `scripts/run_tushare_external_feed_ingest.py`
- `src/quant_robot/data/ingest/tushare_external_feeds.py`
- `src/quant_robot/ops/external_macro_lpr_repair.py`
- `tests/unit/test_external_macro_lpr_repair.py`
- `tests/unit/test_external_macro_lpr_repair_cli.py`
- `tests/unit/test_tushare_external_feed_ingest.py`
- `tests/unit/test_tushare_external_feed_ingest_cli.py`

Implemented:

- Offline repair CLI now exits `3` when the repair report status is blocked.
- LPR cache validation now requires numeric plausible rates with `0 < lpr_1y < 20` and `0 < lpr_5y < 20`.
- Tushare ingest refreshes non-numeric or implausible LPR cache rows instead of reusing them.
- Offline repair rejects `output_root` equal to or nested under the source processed root.
- Tushare external-feed ingest CLI help warns that report-only mode may still call Tushare when fetching source data or refreshing a missing, empty, or invalid LPR cache.
- Offline LPR repair CLI help states that it does not call providers, requires a fresh empty output root outside the source root, and keeps generated data out of Git.

## Test-First Evidence

New failing tests were added before implementation:

- `test_refuses_output_root_nested_under_source_root`
- `test_rejects_lpr_cache_without_numeric_plausible_rates`
- `test_cli_returns_nonzero_when_repair_report_is_blocked`
- `test_help_mentions_fresh_output_root_and_no_provider_calls`
- `test_non_numeric_or_implausible_lpr_cache_is_refreshed`
- `test_help_warns_report_only_can_still_call_provider`

Observed red evidence:

- Non-numeric or implausible cache rows were reused instead of refreshed.
- Offline repair accepted invalid cache rows.
- Blocked repair reports returned exit code `0`.
- CLI help did not contain the safety language.

Focused green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_external_macro_lpr_repair tests.unit.test_external_macro_lpr_repair_cli tests.unit.test_tushare_external_feed_ingest tests.unit.test_tushare_external_feed_ingest_cli tests.unit.test_external_feed_coverage_audit tests.unit.test_external_feed_coverage_audit_cli
```

Result:

- 26 tests passed.

Additional local verification:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_macro_lpr_repair.py --help
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --help
.\.venv\Scripts\python.exe -m py_compile src\quant_robot\ops\external_macro_lpr_repair.py src\quant_robot\data\ingest\tushare_external_feeds.py scripts\run_external_macro_lpr_repair.py scripts\run_tushare_external_feed_ingest.py
```

Both help outputs include the new safety text; compile exited `0`.

## Decision

No provider-consuming step is approved now.

Blocked:

- analyst April cache;
- LPR provider refresh;
- external-feed IC or factor prescreen;
- portfolio grids;
- promotion gates;
- final-holdout reads;
- old northbound accumulation, northbound crowding/reversal, margin-credit, or LPR factor revival.

Allowed next work:

- collect or import real required quota packs from `highspec_desktop` and `laptop`;
- improve operator docs and placeholder safety;
- wait for a valid provider-use window;
- only after explicit provider permission, run report-only LPR cache refresh with isolated cache path.

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
