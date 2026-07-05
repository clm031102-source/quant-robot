# Round524 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 21 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round523 completed with Quant PM agent `Gibbs` and ordinary-user agent `Heisenberg`.
- Next review-agent checkpoint: round 30 after the Round504 baseline, due in Round533.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest quota state: Round524 safe cache-CLI dry-run on 2026-07-05 still blocked with `daily_provider_request_budget_exhausted`, counted 2 same-day provider request windows, had 0 remaining request windows, included `quota_pack_provenance`, skipped 2 duplicate evidence rows, and exited `3`.
- Latest gate state: startup context clear, Quant PM startup `ready`, CN stock factor-mining startup `cleared`, and CN stock data manifest had no blockers.
- Latest full profile: `scripts/run_checks.py --profile laptop-integration --execute` passed with 98 unit tests, Python compile, project audit, and laptop project-sync audit.

## Next Best Target

If still on 2026-07-05 with no new workstation quota packs or manual same-day quota confirmations, do not repeat the same cache dry-run. It has already failed closed in Round523 and Round524 on the same quota day.

Pick one useful non-provider action:

- collect or document `highspec_desktop` and `laptop` quota-pack availability;
- prepare the frozen January-April prescreen command and evidence checklist without running prescreen;
- strengthen cross-machine quota waiting docs;
- wait until the local quota date changes, then run one actual-date `--quota-preflight-only` dry-run.

## Before Any Command

Run these local gates first:

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-profit-mining-20260704 --commits-allowed --pushes-allowed --confirm-start
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py
```

Stop if any gate has blockers. The CN stock data manifest may return `review_required`; read warnings before continuing.

## Quota Dry-Run Rule

Run this only after the local quota date changes or after new cross-machine quota evidence is added:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round525_analyst_report_revision_cache_202404_<YYYYMMDD> --processed-output-dir data\processed\round525_analyst_report_revision_cache_202404_<YYYYMMDD> --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round525_cache_cli_quota_preflight_<YYYYMMDD> --quota-preflight-only
```

Replace `<YYYYMMDD>` with the actual local date. Stop if it exits `3`.

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

## Cross-Machine Quota Checklist

Before a provider-backed cache attempt, fill this in from quota packs or direct confirmation:

| Machine | Pack path or unavailable reason | Confirmation time | Confirmed by | Status |
|---|---|---|---|---|
| `office_desktop` | `data\reports\round521_analyst_quota_pack_provenance_20260705` | 2026-07-05 | Codex | available |
| `highspec_desktop` | unknown | unknown | unknown | stop until known |
| `laptop` | unknown | unknown | unknown | stop until known |

If any relevant machine is unknown, stop before provider-backed caching. A quota pack is local evidence only; it is not a global provider-quota guarantee.

## Provider-Backed Cache Criteria

Run provider-backed April cache only when all of these are true:

- fresh gates have no blockers;
- actual-date cache CLI dry-run exits `0`;
- `target_date_matches_generated_at=true`;
- `remaining_request_windows >= 1`;
- all available quota packs are included with repeated `--quota-report-root`;
- missing workstation packs have manual same-day confirmations;
- no `quota_target_date_differs_from_generated_at` warning is present;
- no one proposes `--skip-quota-preflight`.

## Prescreen Boundary

Do not run prescreen until April cache actually succeeds. A prescreen pass is source-quality evidence only; it is not a research lead, not portfolio evidence, and not promotion evidence.

If April cache succeeds, rerun the frozen January-April prescreen once. If `research_lead_count=0`, run family review. If multiple-testing leads also remain `0`, rotate to a new PIT source candidate plan.

## Stop Or Rotate Conditions

- Stop if the cache CLI exits `3`.
- Stop if `report_rc` hits provider quota or rate limit.
- Stop if row-cap warnings require smaller windows.
- Stop if startup gate or data manifest has blockers.
- Stop if cross-machine quota packs are unavailable and same-day provider usage cannot be manually confirmed.
- Stop if `quota_target_date_differs_from_generated_at` appears during provider-backed cache execution.
- Stop if `skip_quota_preflight_requires_cached_processed_windows` appears; do not use skip to fetch missing windows.
- Run a family review if January-April still has `research_lead_count=0`.
- Prepare rotation if multiple-testing leads remain 0.
