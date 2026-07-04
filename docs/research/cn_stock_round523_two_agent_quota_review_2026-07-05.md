# Round523 Two-Agent Quota Review

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Machine/task: `office_desktop` / `factor_batch`

## Purpose

Round523 completed the required round-20 review checkpoint after the Round504 baseline. The checkpoint used two read-only reviewers:

- Quant PM reviewer `Gibbs`
- Ordinary inexperienced-user reviewer `Heisenberg`

No reviewer edited files, staged changes, committed, pushed, or ran provider-backed Tushare/cache/factor jobs.

## Quant PM Verdict

The Quant PM verdict was conservative:

- Wait for quota reset; provider-backed April cache is not allowed while the actual-date cache CLI dry-run exits `3`.
- Treat quota preflight as `local_report_roots_only`, not as a global Tushare quota oracle.
- Before any April cache attempt, require fresh startup/data gates, all available workstation quota packs via repeated `--quota-report-root`, `target_date_matches_generated_at=true`, visible `quota_pack_provenance`, auditable duplicate evidence, listed `report_roots`, and `--quota-preflight-only` exit `0`.
- Do not use bypasses: no normal-fetch `--skip-quota-preflight`, no nonlocal `--quota-target-date` for provider-backed execution, no formula tuning, no portfolio grids, no promotion gates, and no final-holdout reads.
- April should be one frozen check if quota allows, not a new research campaign.
- If January-April still has `research_lead_count=0`, run family review. If multiple-testing leads are also `0`, rotate to a genuinely new PIT source candidate plan.

## Ordinary User Verdict

The ordinary-user reviewer found that the safety path was understandable but still too easy to misuse:

- Startup gates were not prominent enough before cache commands.
- Standalone preflight help did not explain that blocked preflight exits `0` unless `--fail-on-blocked` is used.
- Standalone preflight help under-described `--report-root`, `--target-date`, `--max-daily-requests`, and local-only scope.
- Angle-bracket placeholders were risky for PowerShell copy-paste.
- Cross-machine quota confirmation needed a concrete checklist.
- Safe dry-run and real provider-backed cache commands still looked too similar.
- `--request-sleep-seconds 0` and `--continue-after-rate-limit` needed stronger quota-path warnings.
- Quota pack export help needed to say generated pack output is shared out of band and not committed.
- Round checkpoint artifacts needed an explicit expected document shape.
- Prescreen success needed to be framed as source-quality evidence only, not promotion evidence.

## Help Hardening

Round523 added test-covered CLI help hardening:

- `scripts/run_analyst_report_quota_preflight.py --help` now says it does not call Tushare, covers local report roots only, explains repeated `--report-root` for quota packs, and clarifies `--fail-on-blocked` exit-code behavior.
- `scripts/run_tushare_analyst_report_cache.py --help` now labels the quota-constrained analyst-report path: `--request-sleep-seconds 0` is only for a single monthly window after quota preflight allows it, and `--continue-after-rate-limit` should not be used there.
- `scripts/export_analyst_report_quota_pack.py --help` now says it writes generated `data/reports` evidence, should be shared out of band, and should not be committed.

Test-first evidence:

- `test_cache_cli_help_explains_quota_safe_modes` failed first because the quota-constrained path warning was missing.
- `test_standalone_preflight_help_explains_exit_codes_and_scope` failed first because standalone preflight help did not mention Tushare-free local scope or exit-code behavior.
- `test_exporter_help_explains_generated_pack_safety` failed first because the exporter help did not mention generated evidence, out-of-band sharing, or do-not-commit safety.
- After implementation, the focused help and quota-pack suites passed with 25 tests.

## Startup And Safety Gates

Fresh gate evidence on 2026-07-05:

- Startup context: current branch matched `codex/factor-batch-cn-stock-profit-mining-20260704`; upstream sync `0 0`.
- Quant PM startup gate: `status="ready"`, blockers `[]`, required reading `7/7`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: rerun with `--commits-allowed --pushes-allowed --confirm-start`; `status="cleared"` and blockers `[]`.
- CN stock data manifest: `status="review_required"`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`; bars covered 2015-01-05 through 2026-06-15, and moneyflow coverage remained below bars.

Safety boundary remains unchanged: research-to-paper only, no broker connection, no live account reads, no order placement, and no automatic live trading.

## Real Quota Evidence

Round523 safe cache-CLI dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round523_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round523_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-output-dir data\reports\round523_cache_cli_quota_preflight_20260705 --quota-preflight-only
```

Result:

- `LASTEXITCODE=3`
- `status="blocked"`
- blocker: `daily_provider_request_budget_exhausted`
- `target_date_matches_generated_at=true`
- `quota_scope="local_report_roots_only"`
- `cache_report_count=2`
- `counted_provider_request_windows=2`
- `duplicate_evidence_rows=2`
- `quota_pack_root_count=1`
- `remaining_request_windows=0`
- scanned roots: `data\reports`, `data\reports\round521_analyst_quota_pack_provenance_20260705`
- pack provenance: `office_desktop` / `factor_batch` / `codex/factor-batch-cn-stock-profit-mining-20260704`

No provider-backed cache execution occurred.

## Verification

Focused verification passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analyst_report_quota_preflight.py tests\unit\test_analyst_report_quota_pack.py -q
```

Result: 25 tests passed.

Full laptop-integration verification passed before commit:

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop-integration --execute
```

Result: 98 unit tests passed, Python compile completed, project audit passed, and laptop project-sync audit reported only syncable code/test/doc paths.

## Decision

Do not run the April 2024 provider-backed analyst-report cache on 2026-07-05. The only allowed next cache-related action is another actual-date `--quota-preflight-only` dry-run after quota plausibly resets and after all workstation quota packs or manual same-day confirmations are accounted for.

If that dry-run exits `0`, run exactly one April cache with the same quota roots and without `--quota-preflight-only`. If the frozen January-April prescreen still has `research_lead_count=0`, run family review; if multiple-testing leads also remain `0`, rotate to a new PIT source plan.
