# CN Stock Round534 Operator Runbook Hardening

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 31 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, did not write repaired processed data, and did not touch final holdout. It converted the Round533 review feedback into a safer operator runbook.

## Startup Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 05:27:39 +08:00.
- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Git status before work: clean and synchronized with origin.
- Startup context: branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Objective

Round533 found that the source-tooling path was mostly guarded in code, but still too easy to misuse from the command line. Round534 therefore records a copy-safe operator sequence with explicit variables, preflight checks, stop conditions, and provider-disabled defaults.

This is an operator-safety document only. It is not source-quality evidence, factor evidence, portfolio evidence, promotion evidence, or final-holdout evidence.

## Always Start Here

Use this block at the start of the next continuation before any provider, data, cache, repair, factor, or promotion command:

```powershell
$MACHINE = "office_desktop"
$TASK = "factor_batch"
$BRANCH = "codex/factor-batch-cn-stock-profit-mining-20260704"
$RUN_DATE = "20260705"

git status --short --branch
git ls-files data/raw data/processed data/reports

.\.venv\Scripts\python.exe scripts\start_task_context.py --machine $MACHINE --task $TASK --branch $BRANCH
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine $MACHINE --task $TASK --branch $BRANCH
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine $MACHINE --task $TASK --branch $BRANCH --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Required preflight result:

- `git status --short --branch` shows the intended branch and no unrelated working-tree changes.
- `git ls-files data/raw data/processed data/reports` prints no tracked generated data paths.
- Startup context is synchronized with origin.
- Quant PM startup gate is `ready`.
- Factor-mining startup gate is `cleared`.
- CN stock data manifest has no blockers.

Stop if any gate reports blockers, if the branch is not the intended task branch, or if generated data paths are tracked.

## Decision Table

| State | Operator Action |
| --- | --- |
| Required analyst quota packs missing from `highspec_desktop` or `laptop` | Stop provider-backed analyst cache. Import real packs or keep waiting. |
| Same-day provider request budget exhausted | Do not run provider-backed cache and do not repeat equivalent same-day dry-runs. |
| Local quota date changed and required packs are complete | Run one actual-date analyst cache preflight first. Do not execute cache unless preflight exits `0`. |
| Analyst preflight exits `3` | Stop. Treat the report as a block, not as a partial approval. |
| April analyst cache succeeds | Run the frozen January-April prescreen exactly once, then review zero-lead or lead outcomes. |
| LPR cache missing, empty, non-numeric, or implausible | Stop unless provider LPR refresh is explicitly approved for this continuation. |
| LPR cache has plausible non-missing `lpr_1y` and `lpr_5y` | Offline repair may run into a fresh ignored output root. |
| Offline repair exits `3` or nonzero | Stop. Do not audit repaired coverage or run factors. |
| Repaired coverage audit fails | Stop. Keep LPR and macro-rate factors blocked. |
| Repaired coverage audit passes | Record source-quality evidence only. A new candidate plan is still required before factor tests. |
| Any command creates `data/raw`, `data/processed`, or `data/reports` output | Leave generated output unstaged and rerun `git status --short`. |

## Analyst Cache Preflight Block

This is a future dry-run block. It should be used only after the local quota date changes or real missing-machine packs have been imported.

```powershell
$MACHINE = "office_desktop"
$BRANCH = "codex/factor-batch-cn-stock-profit-mining-20260704"
$RUN_DATE = "20260705"
$REPORT_ROOT = "data\reports"
$PACK_ROOT = "data\reports\round521_analyst_quota_pack_provenance_20260705"
$OUT_REPORT = "data\reports\round534_analyst_report_revision_cache_202404_$RUN_DATE"
$OUT_PROCESSED = "data\processed\round534_analyst_report_revision_cache_202404_$RUN_DATE"
$OUT_QUOTA = "data\reports\round534_required_machine_quota_preflight_$RUN_DATE"

.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py `
  --start-date 2024-04-01 `
  --end-date 2024-04-30 `
  --output-dir $OUT_REPORT `
  --processed-output-dir $OUT_PROCESSED `
  --window-frequency MS `
  --request-sleep-seconds 0 `
  --max-rows-per-window 5000 `
  --quota-report-root $REPORT_ROOT `
  --quota-report-root $PACK_ROOT `
  --quota-output-dir $OUT_QUOTA `
  --quota-required-pack-machine office_desktop `
  --quota-required-pack-machine highspec_desktop `
  --quota-required-pack-machine laptop `
  --quota-pack-machine-note "highspec_desktop=not_available_20260705_0527_no_pack_imported" `
  --quota-pack-machine-note "laptop=not_available_20260705_0527_no_pack_imported" `
  --quota-preflight-only

if ($LASTEXITCODE -eq 3) { throw "Analyst quota preflight blocked; do not execute provider cache." }
if ($LASTEXITCODE -ne 0) { throw "Analyst quota preflight failed with exit code $LASTEXITCODE." }
```

This preflight-only command is not authorization to execute the cache. Cache execution still requires complete required-machine evidence, an actual-date preflight exit `0`, and explicit provider-use permission for that continuation.

## LPR Provider Refresh Fence

Report-only external-feed ingest may still call Tushare when source data or LPR cache refresh is needed. Keep the provider fence false unless the continuation explicitly approves provider use.

```powershell
$ALLOW_PROVIDER_REFRESH = $false
if (-not $ALLOW_PROVIDER_REFRESH) { throw "Provider LPR refresh is not authorized for this continuation." }

$RUN_DATE = "20260705"
$LPR_REPORT = "data\reports\round534_external_feed_lpr_report_only_20240701_$RUN_DATE"
$LPR_CACHE = "data\reports\round534_external_lpr_cache_refresh_$RUN_DATE\external_lpr_cache.json"
$LPR_PROGRESS = "$LPR_REPORT\progress.jsonl"

.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py `
  --start-date 2024-07-01 `
  --end-date 2024-07-01 `
  --output-dir $LPR_REPORT `
  --lpr-cache-path $LPR_CACHE `
  --progress-jsonl $LPR_PROGRESS
```

After any provider refresh attempt, record the exit code, provider progress status, and `git status --short`. Generated data remains out of Git.

## LPR Cache Check

Run this check before any offline repair:

```powershell
$LPR_CACHE = "data\reports\round534_external_lpr_cache_refresh_20260705\external_lpr_cache.json"

@'
import json
import sys

def ok_rate(value):
    try:
        rate = float(value)
    except Exception:
        return False
    return 0 < rate < 20

with open(sys.argv[1], encoding="utf-8") as handle:
    rows = json.load(handle).get("rows", [])

ok = any(ok_rate(row.get("lpr_1y")) and ok_rate(row.get("lpr_5y")) for row in rows)
print({"rows": len(rows), "has_plausible_lpr": ok})
sys.exit(0 if ok else 3)
'@ | .\.venv\Scripts\python.exe - $LPR_CACHE

if ($LASTEXITCODE -eq 3) { throw "LPR cache does not contain plausible non-missing rates." }
if ($LASTEXITCODE -ne 0) { throw "LPR cache check failed with exit code $LASTEXITCODE." }
```

## Offline Repair And Coverage Gate

Run this only after the LPR cache check exits `0`. It does not call providers, but it writes ignored processed/report output.

```powershell
$RUN_DATE = "20260705"
$SOURCE_ROOT = "data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623"
$LPR_CACHE = "data\reports\round534_external_lpr_cache_refresh_$RUN_DATE\external_lpr_cache.json"
$REPAIR_ROOT = "data\processed\round534_external_feeds_lpr_repaired_$RUN_DATE"
$REPAIR_REPORT = "data\reports\round534_external_macro_lpr_repair_$RUN_DATE"
$AUDIT_REPORT = "data\reports\round534_external_feed_lpr_repair_coverage_audit_$RUN_DATE"

.\.venv\Scripts\python.exe scripts\run_external_macro_lpr_repair.py `
  --processed-root $SOURCE_ROOT `
  --lpr-cache-path $LPR_CACHE `
  --output-root $REPAIR_ROOT `
  --report-dir $REPAIR_REPORT `
  --market CN `
  --copy-other-feeds

if ($LASTEXITCODE -eq 3) { throw "Offline LPR repair report is blocked." }
if ($LASTEXITCODE -ne 0) { throw "Offline LPR repair failed with exit code $LASTEXITCODE." }

.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py `
  --processed-root $REPAIR_ROOT `
  --output-dir $AUDIT_REPORT `
  --market CN

git status --short
```

Coverage pass is not alpha approval. It only reclassifies the repaired LPR path from blocked source coverage to source-quality evidence eligible for a later preregistered candidate plan.

## Git And Data Boundary

Before staging any code or docs after a data command:

```powershell
git status --short
git ls-files data/raw data/processed data/reports
```

Safe staging rule:

- Stage code, configs, tests, and lightweight docs only.
- Do not stage generated `data/raw`, `data/processed`, `data/reports`, Parquet, CSV, logs, tokens, broker credentials, account data, or order data.
- If generated data appears in `git status`, leave it unstaged unless a future approved cleanup explicitly removes ignored artifacts.

## Decision

Round534 keeps provider-consuming work blocked. The next useful work is one of:

- import real quota packs from `highspec_desktop` and `laptop`;
- wait for the local quota date to change, then run exactly one actual-date analyst quota preflight;
- use the LPR provider refresh fence only after explicit provider approval;
- otherwise continue non-provider documentation, tests, or source-tooling hardening.

Do not run analyst April cache, LPR provider refresh, external-feed factors, portfolio grids, promotion gates, or final holdout from this document alone.

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
