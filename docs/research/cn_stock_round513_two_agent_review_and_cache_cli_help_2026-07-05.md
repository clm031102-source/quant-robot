# CN Stock Round513 Two-Agent Review And Cache CLI Help

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 10 after the Round504 review-agent baseline. This round completed the required two-agent review checkpoint and acted on the most immediate usability risk.

## Review Agents

Two read-only agents reviewed the project:

- Quant PM review agent: `Turing`
- Ordinary inexperienced user review agent: `Maxwell`

Neither agent edited files or ran provider-backed downloads.

## Quant PM Review

Direction:

- Continue only narrowly and conditionally.
- This remains a research-to-paper source-smoke lane, not a promotion lane.
- The April 2024 analyst-report cache is allowed only after actual-date `--quota-preflight-only` exits `0`.
- If January-April still has `research_lead_count=0` or multiple-testing leads remain 0, rotate away from this source family.

Top risks:

- Evidence weakened after March: Round505 had 0 multiple-testing leads and 0 research leads.
- Quota preflight is local-report based, so cross-machine same-day `report_rc` usage can be missed if evidence is not present on this machine.
- `--skip-quota-preflight` remains powerful and must stay offline/controlled only.

Red lines:

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March.
- Do not run portfolio grids or promotion gates.
- Do not commit generated data, logs, credentials, account data, or order data.

## Inexperienced User Review

The user-review agent understood the next safe path as:

1. Finish the Round513 two-agent review checkpoint.
2. Run startup gates.
3. Run the April 2024 cache CLI with `--quota-preflight-only`.
4. Cache only if the actual-date preflight exits `0`.
5. Stop on exit `3`.

Confusion points:

- The checklist commands are machine-specific and use `office_desktop`.
- The safe dry-run command and real provider-backed cache command look almost identical.
- CLI `--help` listed flags but did not explain quota modes, `exit 3`, or the difference between `--quota-preflight-only` and `--skip-quota-preflight`.
- `<date>` placeholders needed clearer examples.

## Round513 Action

The highest-value immediate action was to make the cache CLI safer for an ordinary user before any future cache attempt:

- Added explicit help text for quota options in `scripts/run_tushare_analyst_report_cache.py`.
- Help now says the command runs local preflight by default and exits `3` when blocked.
- `--quota-preflight-only` help now states it does not call Tushare.
- `--skip-quota-preflight` help now says it is for exceptional offline or controlled local replay only.
- `--skip-quota-preflight-reason` help now says it is required when skipping.

Test-first evidence:

```text
tests/unit/test_analyst_report_quota_preflight.py::AnalystReportQuotaPreflightTests::test_cache_cli_help_explains_quota_safe_modes
AssertionError: 'does not call Tushare' not found
```

After implementation:

```text
tests/unit/test_analyst_report_quota_preflight.py
11 passed in 3.34s
```

Focused profile verification:

```text
tests/unit/test_analyst_report_quota_preflight.py tests/unit/test_check_plan.py::CheckPlanTests::test_laptop_integration_profile_runs_merged_main_verification_gate
12 passed in 3.40s
```

Final verification:

```text
scripts/run_checks.py --profile laptop-integration --execute
84 passed in 17.70s
```

## Startup And Data Evidence

Fresh 2026-07-05 gates:

- Startup context: `office_desktop`, `factor_batch`, branch `codex/factor-batch-cn-stock-profit-mining-20260704`, upstream sync `0	0`.
- Quant PM startup gate: `status=ready`, no blockers.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, no blockers.
- CN stock data manifest: no blockers, `status=review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Real Cache-CLI Evidence

Actual-date cache CLI preflight-only run:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-04-01 --end-date 2024-04-30 --output-dir data\reports\round513_analyst_report_revision_cache_202404_20260705 --processed-output-dir data\processed\round513_analyst_report_revision_cache_202404_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000 --quota-target-date 2026-07-05 --quota-output-dir data\reports\round513_cache_cli_quota_preflight_20260705 --quota-preflight-only
```

Result:

- Status: `blocked`
- Request allowed: false
- Blockers: `daily_provider_request_budget_exhausted`
- Counted provider request windows: 2
- Remaining request windows: 0
- Exit code: `3`

The command stopped before calling Tushare.

## Decision

Do not run the April 2024 provider-backed analyst-report cache on 2026-07-05. The actual-date preflight-only command still exits `3`.

Next direction:

- After quota plausibly resets, run the cache CLI with `--quota-preflight-only` first.
- If it exits `3`, stop.
- If it exits `0`, remove only `--quota-preflight-only` and cache April 2024 once.
- After January-April prescreen, rotate if `research_lead_count=0` or multiple-testing leads remain 0.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
