# CN Stock Round696 External HK-Hold LPR Candidate-Plan Feasibility

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round696 checked whether the Round695 repaired LPR source can immediately support a new candidate-plan gate. The conclusion is no for an active stock cross-sectional candidate: LPR regime-control source is ready, but the only plausible stock-level interaction, HK-hold x LPR, remains short of the preregistered 60-observation history requirement.

This round did not run IC tests, portfolio grids, promotion gates, final-holdout reads, sign flips, or threshold tuning.

## Starting Point

Round695 repaired `external_macro_rates` LPR coverage under:

```text
data/processed/round695_external_feeds_lpr_repaired_20260709
```

The Round695 source join smoke used:

```text
configs/external_feed_lpr_regime_source_preregistration_round695_20260709.json
```

That smoke produced:

- 2 passing macro regime-control seeds.
- 1 HK-hold x LPR interaction seed with `insufficient_history`.
- 0 available-date violations.
- 0 same-day or future raw-date violations.

## HK-Hold Date Distribution

Current HK-hold rows in the repaired root:

| Metric | Value |
| --- | ---: |
| Rows | 134,461 |
| Unique dates | 40 |
| First date | 2024-07-02 |
| Last date | 2025-12-31 |

The 40 dates are concentrated in 2024-07-02 through 2024-08-16, plus quarter-end dates:

- 2024-09-30
- 2024-12-31
- 2025-03-31
- 2025-06-30
- 2025-09-30
- 2025-12-31

## Extension Probes

### 2024-10 Executed Write Probe

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --start-date 2024-10-01 --end-date 2024-10-31 --output-dir data\processed\round695_external_feeds_lpr_repaired_20260709 --lpr-cache-path data\reports\round695_external_lpr_cache_refresh_20260709\external_lpr_cache.json --report-copy-dir data\reports\round696_external_feed_hk_hold_backfill_202410_20260709 --progress-jsonl data\reports\round696_external_feed_hk_hold_backfill_202410_20260709\progress.jsonl --execute-write-processed
```

Result:

- Exit code: `0`
- Processed writes enabled: true
- `external_hk_hold`: warn / empty feed
- Dropped non-CN HK-hold symbols: 13,853
- Added usable HK-hold CN rows: 0
- Other feeds passed and were appended to the ignored repaired root.

### 2024-08-19 Report-Only Probe

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --start-date 2024-08-19 --end-date 2024-08-19 --output-dir data\reports\round696_external_feed_hk_hold_probe_20240819_20260709 --lpr-cache-path data\reports\round695_external_lpr_cache_refresh_20260709\external_lpr_cache.json --progress-jsonl data\reports\round696_external_feed_hk_hold_probe_20240819_20260709\progress.jsonl
```

Result:

- Exit code: `0`
- Processed writes enabled: false
- `external_hk_hold`: warn / empty feed
- Dropped non-CN HK-hold symbols: 792
- Added usable HK-hold CN rows: 0

Interpretation: the missing HK-hold days are not solved by blindly extending adjacent dates. The endpoint can return non-CN rows that the CN stock pipeline correctly drops.

## Current Repaired Root After Probe

Coverage command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --output-dir data\reports\round696_external_feed_after_hk_hold_extension_probe_coverage_audit_20260709 --market CN
```

Result:

- Audited feeds: 2
- Pass count: 2
- Blocked count: 0
- `external_macro_rates.status=pass`
- LPR non-null ratio: 1.0
- `lpr_1y_non_null_rows=344`
- `lpr_5y_non_null_rows=344`
- HK-hold unique observation dates: 40

Join-smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --seed-config configs\external_feed_lpr_regime_source_preregistration_round695_20260709.json --output-dir data\reports\round696_external_lpr_regime_after_hk_hold_extension_probe_join_smoke_20260709 --market CN --signal-start-date 2024-07-01 --signal-end-date 2025-12-31
```

Result:

- Seed count: 3
- Pass count: 2
- Insufficient-history count: 1
- Available-date violations: 0
- Same-day or future raw-date violations: 0
- HK-hold x LPR remains `insufficient_history`, with 40 primary observation dates versus 60 required.

## Candidate-Plan Decision

Do not run a candidate-plan gate for HK-hold x LPR yet.

Reasons:

- The active stock-level interaction seed remains short of the preregistered history requirement.
- Lowering the 60-observation requirement after seeing the join-smoke result would be post-result threshold tuning.
- Pure LPR seeds are market-level regime controls, not standalone stock-ranking candidates; treating them as active cross-sectional factors would misuse the factor-mining candidate-plan gate.
- Old northbound accumulation, northbound crowding/reversal, and margin-credit families remain hibernated.

Allowed next actions:

- Investigate why `hk_hold` returns CN rows for 2024-07 through 2024-08-16 and quarter-end dates, but non-CN rows for tested adjacent dates.
- Add a source-audit tool that records raw HK-hold symbol-type composition before CN filtering.
- If a valid HK-hold extension path is found, rerun coverage and join smoke without changing the preregistered 60-observation threshold.
- Separately design an LPR regime-control validation plan only as a market-regime gate for an already valid cross-sectional factor, not as standalone alpha.

Blocked actions:

- No HK-hold x LPR IC screen before history readiness.
- No standalone LPR stock rank.
- No old external northbound or margin reentry.
- No portfolio grid, promotion gate, or final-holdout read from source probes.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
