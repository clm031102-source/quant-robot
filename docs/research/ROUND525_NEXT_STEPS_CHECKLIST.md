# Round525 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 22 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round523 completed with Quant PM agent `Gibbs` and ordinary-user agent `Heisenberg`.
- Next review-agent checkpoint: round 30 after the Round504 baseline, due in Round533.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota tooling: quota preflight and cache CLI now support required quota-pack source machines.
- Latest quota state: Round525 safe cache-CLI dry-run with required machines blocked with `daily_provider_request_budget_exhausted` and `missing_required_quota_pack_machines`.
- Missing required quota pack machines: `highspec_desktop`, `laptop`.
- Present quota pack machines: `office_desktop`.
- Latest full profile: `scripts/run_checks.py --profile laptop-integration --execute` passed with 100 unit tests, Python compile, project audit, and laptop project-sync audit.

## Next Best Target

If still on 2026-07-05, do not run provider-backed cache. The next useful work is to collect or document missing workstation quota-pack evidence for:

- `highspec_desktop`
- `laptop`

If those packs cannot be produced, record the unavailable reason and confirmation timestamp before any provider-backed cache attempt. If the local quota date changes, rerun one actual-date preflight with required-machine constraints before any cache execution.

## Before Any Command

Run these local gates first:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Stop if any gate has blockers. The CN stock data manifest may return `review_required`; read warnings before continuing.

## Required-Machine Dry-Run

Run this only after the local quota date changes or after new cross-machine quota evidence is added:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round526_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round526_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round526_required_machine_quota_preflight_<YYYYMMDD> --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-preflight-only
```

Replace `<YYYYMMDD>` with the actual local date. Stop if it exits `3`.

## Provider-Backed Cache Criteria

Run provider-backed April cache only when all of these are true:

- fresh gates have no blockers;
- actual-date cache CLI dry-run exits `0`;
- `target_date_matches_generated_at=true`;
- `remaining_request_windows >= 1`;
- all available quota packs are included with repeated `--quota-report-root`;
- `missing_required_quota_pack_machines=[]`;
- `present_quota_pack_machines` includes `office_desktop`, `highspec_desktop`, and `laptop`;
- no `quota_target_date_differs_from_generated_at` warning is present;
- no one proposes `--skip-quota-preflight`.

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
- Do not use `--continue-after-rate-limit` in this quota-constrained analyst-report path.
- Do not use nonlocal `--quota-target-date` for provider-backed cache execution.

## Prescreen Boundary

Do not run prescreen until April cache actually succeeds. A prescreen pass is source-quality evidence only; it is not a research lead, not portfolio evidence, and not promotion evidence.

If April cache succeeds, rerun the frozen January-April prescreen once. If `research_lead_count=0`, run family review. If multiple-testing leads also remain `0`, rotate to a new PIT source candidate plan.
