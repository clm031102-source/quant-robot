# CN Stock Round695 External LPR Source Readiness

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round695 followed the local Round692-694 review direction: stop adjacent statement-ratio factor mining and audit whether a genuinely different PIT source is ready. This round repaired and smoke-tested the external macro LPR source. It did not run factor IC tests, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, or 2026 final-holdout reads.

## Startup And Gate Evidence

- Startup context: passed for `office_desktop` / `factor_batch`.
- Quant PM startup gate: `ready`, blockers `[]`, primary research market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`, branch matched `codex/factor-batch-cn-stock-source-readiness-round695-20260709`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.

## Prior Local Direction Evidence

The local Round692-694 review kept these exact standalone families hibernated:

- `financial_reporting_timeliness`
- `pead_gap_reversal_source_repair`
- `statement_working_capital_pressure`
- `statement_capital_structure_efficiency`

The already-generated Round507 analyst-report frozen January-April prescreen also remained non-promotable:

| Metric | Value |
| --- | ---: |
| Report rows | 6,828 |
| Report assets | 1,789 |
| Candidate count | 4 |
| Test count | 8 |
| Multiple-testing leads | 0 |
| Neutral-gate passes | 0 |
| Research leads | 0 |
| Promotion allowed | 0 |

Round695 analyst quota preflight on 2026-07-09 still blocked new provider-backed analyst cache work because required quota packs were missing from `highspec_desktop` and `laptop`, even though local same-day request windows were available.

## External Feed Before Repair

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --output-dir data\reports\round695_external_feed_coverage_audit_20260709 --market CN
```

Result:

- HK-hold coverage: pass, 134,461 rows, 40 observation dates, 3,980 symbols.
- Macro rates: blocked, 340 rows, 0 non-null `lpr_1y`, 0 non-null `lpr_5y`.
- Blocker: `lpr_non_missing_coverage_below_threshold`.
- External-feed IC or portfolio allowed: false.

## LPR Cache Refresh

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --start-date 2024-07-01 --end-date 2024-07-01 --output-dir data\reports\round695_external_feed_lpr_report_only_20240701_20260709 --lpr-cache-path data\reports\round695_external_lpr_cache_refresh_20260709\external_lpr_cache.json --progress-jsonl data\reports\round695_external_feed_lpr_report_only_20240701_20260709\progress.jsonl
```

Result:

- Report-only run exited `0`.
- `processed_writes_enabled=false`.
- `shibor_lpr` returned 1,527 rows.
- Single-day `external_macro_rates` quality passed.
- No `data/processed` output was written by this provider call.

## Offline LPR Repair

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_macro_lpr_repair.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --lpr-cache-path data\reports\round695_external_lpr_cache_refresh_20260709\external_lpr_cache.json --output-root data\processed\round695_external_feeds_lpr_repaired_20260709 --report-dir data\reports\round695_external_macro_lpr_repair_20260709 --market CN --copy-other-feeds
```

Result:

- Status: `pass`
- Blockers: `[]`
- Macro rows: 340
- LPR cache rows used by repair: 79
- `lpr_1y` non-null before / after: 0 / 340
- `lpr_5y` non-null before / after: 0 / 340
- Copied other feeds: `external_margin_detail`, `external_hk_hold`, `external_hsgt_flow`, `external_index_state`
- Promotion allowed: false

Generated repaired data is under `data/processed` and must stay out of Git.

## Repaired Source Coverage

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --output-dir data\reports\round695_external_feed_lpr_repaired_coverage_audit_20260709 --market CN
```

Result:

- Audited feeds: 2
- Pass count: 2
- Blocked count: 0
- Blockers: `[]`
- `external_macro_rates.status=pass`
- LPR non-null ratio: 1.0
- `lpr_1y_non_null_rows=340`
- `lpr_5y_non_null_rows=340`
- Source-audit field `external_feed_ic_or_portfolio_allowed=true`

This is source readiness only. It is not IC evidence, portfolio evidence, promotion evidence, or live evidence.

## LPR Source Join Smoke

Added source-level config:

```text
configs/external_feed_lpr_regime_source_preregistration_round695_20260709.json
```

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --seed-config configs\external_feed_lpr_regime_source_preregistration_round695_20260709.json --output-dir data\reports\round695_external_lpr_regime_join_smoke_20260709 --market CN --signal-start-date 2024-07-01 --signal-end-date 2025-12-31
```

Summary:

- Seed count: 3
- Pass count: 2
- Insufficient-history count: 1
- Joined rows: 1,995,559
- Available-date violations: 0
- Same-day or future raw-date violations: 0
- Promotion allowed: false

Seed details:

| Seed | Status | Joined rows | Signal dates | Notes |
| --- | --- | ---: | ---: | --- |
| `lpr_term_premium_easing_regime_60` | pass | 548 | 548 | Macro regime-control source only |
| `lpr_shibor_credit_gap_regime_60` | pass | 548 | 548 | Macro regime-control source only |
| `hk_hold_stability_x_lpr_easing_regime_60` | insufficient_history | 1,994,463 | 547 | No PIT leak, but HK-hold has only 40 observation dates versus 60 required |

## Decision

Round695 repaired the external macro LPR source blocker. The repaired root is source-ready for a future candidate-plan discussion of LPR-based market-regime controls.

Do not immediately run IC or portfolio tests from this repair. The next factor-batch step should be a new candidate-plan gate for a genuinely new LPR regime-control or LPR interaction family. That plan must keep promotion disabled, exclude final-holdout tuning, and explicitly avoid:

- standalone market-level LPR stock ranking;
- old northbound accumulation or crowding/reversal reruns;
- old margin-credit reentry;
- lowering the HK-hold history requirement after seeing the join-smoke result;
- treating source coverage or join smoke as alpha evidence.

If the next research direction needs HK-hold x LPR interaction, first extend or validate HK-hold observation history instead of tuning the minimum-history gate down after the fact.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No final-holdout read.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
