# Round533 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 30 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round533 completed with Quant PM reviewer `Hubble` and ordinary-user reviewer `Dirac`.
- Next review-agent checkpoint: round 40 after the Round504 baseline, due in Round543.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota state: Round526 safe cache-CLI dry-run with required machines and notes blocked with `daily_provider_request_budget_exhausted` and `missing_required_quota_pack_machines`.
- Missing required quota pack machines: `highspec_desktop`, `laptop`.
- Present quota pack machines: `office_desktop`.
- Latest Round532 work: offline external macro LPR repair tool added.
- Latest Round533 work: two-agent review completed and LPR repair guardrails hardened.

## Next Best Target

Round534 should be non-provider by default.

Preferred next actions:

- import real quota packs from `highspec_desktop` and `laptop`;
- improve operator docs and command-variable examples;
- wait for a valid provider-use window before any analyst or LPR provider command.

Do not run provider-backed analyst cache, LPR provider refresh, external-feed factors, portfolio grids, promotion gates, or final holdout now.

## Startup Blocks

For normal continuation from `office_desktop / factor_batch`:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

For review-only continuation, use the confirmed machine and `factor_review` instead of `factor_batch`. Do not add commits/pushes flags unless the user explicitly permits write work for that task:

```powershell
$MACHINE = "office_desktop"
$BRANCH = "codex/factor-batch-cn-stock-profit-mining-20260704"
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine $MACHINE --task factor_review --branch $BRANCH
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine $MACHINE --task factor_review --branch $BRANCH
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine $MACHINE --task factor_review --branch $BRANCH --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Stop if any gate has blockers.

## Decision Table

| State | Action |
| --- | --- |
| Required analyst quota packs missing | Stop or import real packs from `highspec_desktop` and `laptop`. |
| Same-day provider budget exhausted | Do not run provider-backed cache or repeat the same dry-run. |
| LPR cache missing, empty, non-numeric, or implausible | Refresh only if provider use is explicitly allowed. |
| LPR cache has non-missing plausible rates | Offline repair may write a fresh ignored processed root. |
| LPR repaired root coverage audit fails | Stop; do not run factors. |
| LPR repaired root coverage audit passes | Treat as source-quality evidence only; candidate plan still required before any factor test. |

## Analyst Required-Machine Dry-Run

Run this only after the local quota date changes or after real cross-machine quota evidence is added.

```powershell
$RUN_DATE = "20260705"
$REPORT_ROOT = "data\reports"
$PACK_ROOT = "data\reports\round521_analyst_quota_pack_provenance_20260705"
$OUT_REPORT = "data\reports\round534_analyst_report_revision_cache_202404_$RUN_DATE"
$OUT_PROCESSED = "data\processed\round534_analyst_report_revision_cache_202404_$RUN_DATE"
$OUT_QUOTA = "data\reports\round534_required_machine_quota_preflight_$RUN_DATE"

.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir $OUT_REPORT --processed-output-dir $OUT_PROCESSED --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root $REPORT_ROOT --quota-report-root $PACK_ROOT --quota-output-dir $OUT_QUOTA --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=<reason and timestamp if still unavailable>" --quota-pack-machine-note "laptop=<reason and timestamp if still unavailable>" --quota-preflight-only
```

Stop if it exits `3`.

## LPR Cache And Repair Gate

Run cache refresh only when provider use is explicitly allowed. Report-only still may call Tushare.

```powershell
$RUN_DATE = "20260705"
$LPR_REPORT = "data\reports\round534_external_feed_lpr_report_only_20240701_$RUN_DATE"
$LPR_CACHE = "data\reports\round534_external_lpr_cache_refresh_$RUN_DATE\external_lpr_cache.json"
$LPR_PROGRESS = "$LPR_REPORT\progress.jsonl"

.\.venv\Scripts\python.exe scripts\run_tushare_external_feed_ingest.py --start-date 2024-07-01 --end-date 2024-07-01 --output-dir $LPR_REPORT --lpr-cache-path $LPR_CACHE --progress-jsonl $LPR_PROGRESS
```

Before repair, verify:

```powershell
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
git status --short
```

Only after the cache has plausible non-missing LPR values, run offline repair into a fresh output root:

```powershell
$REPAIR_ROOT = "data\processed\round534_external_feeds_lpr_repaired_$RUN_DATE"
$REPAIR_REPORT = "data\reports\round534_external_macro_lpr_repair_$RUN_DATE"

.\.venv\Scripts\python.exe scripts\run_external_macro_lpr_repair.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --lpr-cache-path $LPR_CACHE --output-root $REPAIR_ROOT --report-dir $REPAIR_REPORT --market CN --copy-other-feeds
```

Then audit:

```powershell
$AUDIT_REPORT = "data\reports\round534_external_feed_lpr_repair_coverage_audit_$RUN_DATE"
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root $REPAIR_ROOT --output-dir $AUDIT_REPORT --market CN
git status --short
```

Required audit result before any LPR-dependent work:

- `external_macro_rates.status=pass`;
- `lpr_non_null_ratio >= 0.8`;
- `lpr_1y_non_null_rows > 0`;
- `lpr_5y_non_null_rows > 0`;
- generated `data/` output remains unstaged and uncommitted.

## Red Lines

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run portfolio grids or promotion gates.
- Do not commit generated `data/` outputs, Parquet/CSV files, logs, tokens, broker credentials, account data, or order data.
- Do not use `--skip-quota-preflight` for normal provider-backed analyst-report fetches.
- Do not use nonlocal `--quota-target-date` for provider-backed cache execution.
- Do not overwrite existing long-cycle processed external-feed roots in place.

## Stop Conditions

- Stop if the analyst cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if required cross-machine quota packs are unavailable.
- Stop if LPR cache refresh does not produce non-missing plausible `lpr_1y` and `lpr_5y`.
- Stop if offline repair exits nonzero.
- Keep external LPR/macro factors blocked until LPR non-missing coverage is repaired and coverage audit passes.
