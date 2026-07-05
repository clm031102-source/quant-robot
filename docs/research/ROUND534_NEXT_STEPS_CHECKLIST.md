# Round534 Next Steps Checklist

Use this page before continuing from `codex/factor-batch-cn-stock-profit-mining-20260704`.

## Current State

- Current loop round: 31 after the Round504 review-agent baseline.
- Latest required review checkpoint: Round533 completed with Quant PM reviewer `Hubble` and ordinary-user reviewer `Dirac`.
- Next review-agent checkpoint: round 40 after the Round504 baseline, due in Round543.
- Latest analyst source state: January-March 2024 cached and screened.
- Latest analyst quota state: same-day provider budget exhausted; required quota packs from `highspec_desktop` and `laptop` are still missing.
- Present quota pack machines: `office_desktop`.
- Latest external-feed source state: HK-hold source coverage passed as source-quality evidence only; old northbound and margin-credit families remain hibernated.
- Latest LPR state: LPR cache/coverage remains blocked until a plausible non-missing cache is refreshed and offline repair plus coverage audit pass.
- Latest Round534 work: operator runbook hardened with preflight checks, provider fences, exit-code handling, and Git/data boundary checks.

## Next Best Target

Round535 should still be non-provider unless there is new evidence that changes the state:

- real quota packs imported from `highspec_desktop` and `laptop`;
- local quota date changed and one actual-date preflight is justified;
- explicit provider approval for isolated LPR cache refresh.

If none of those are true, continue with non-provider documentation, tests, or source-tooling hardening. Do not run provider-backed analyst cache, LPR provider refresh, external-feed factors, portfolio grids, promotion gates, or final holdout.

## Required Startup Block

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

Stop if the branch is not synchronized, if generated data paths are tracked, or if any gate reports blockers.

## Provider Default

Provider commands are off by default.

```powershell
$ALLOW_PROVIDER_REFRESH = $false
$ALLOW_ANALYST_CACHE_EXECUTION = $false
```

Do not flip either variable to `$true` unless the continuation explicitly allows that provider action and the relevant preflight checks pass.

## Analyst Path

Allowed now:

- import or inspect real required-machine quota packs;
- run a single actual-date `--quota-preflight-only` only after the local quota date changes or required pack evidence changes.

Blocked now:

- analyst April cache execution;
- frozen January-April prescreen;
- analyst formula tuning;
- portfolio grids;
- promotion gates;
- final holdout.

Exit-code handling:

- `0`: preflight command itself passed; still review packet fields before executing any provider cache.
- `3`: blocked; stop and record blocker.
- anything else: failed; stop and inspect logs.

## LPR Path

Allowed only after explicit provider approval:

- report-only LPR cache refresh with an isolated cache path.

Allowed after a plausible LPR cache exists:

- offline repair into a fresh ignored output root;
- coverage audit against that repaired root.

Blocked until coverage audit passes:

- LPR or macro-rate factor tests;
- external-feed IC runs;
- portfolio grids;
- promotion gates.

Required cache condition:

- at least one row has numeric plausible `0 < lpr_1y < 20` and `0 < lpr_5y < 20`.

## Source-Family Boundary

- Old positive northbound accumulation remains hibernated after Round191.
- Old northbound crowding/reversal remains hibernated after Round213.
- Margin-credit remains hibernated after Round193.
- HK-hold coverage improvement is source-quality evidence only.
- SHIBOR may be reviewed only as a regime-control input after long-cycle validation.
- LPR/macro factors remain blocked until repaired source coverage passes.

## Git Boundary

Before any commit:

```powershell
git status --short
git ls-files data/raw data/processed data/reports
```

Commit only code, configs, tests, lightweight docs, and small JSON evidence that is intentionally tracked. Do not stage generated data outputs, Parquet/CSV files, logs, tokens, broker credentials, account data, or order data.

## Stop Conditions

- Stop if startup gates report blockers.
- Stop if branch status is unclear or behind upstream.
- Stop if required quota packs from `highspec_desktop` or `laptop` are missing and a provider-backed analyst cache is being considered.
- Stop if same-day provider budget is exhausted.
- Stop if analyst cache preflight exits `3`.
- Stop if LPR cache is missing, empty, non-numeric, or implausible.
- Stop if offline repair exits `3` or nonzero.
- Stop if repaired coverage audit fails.
- Stop if any generated data output is accidentally tracked.

## Round543 Reminder

Round543 is the next required two-agent checkpoint. If the loop reaches Round543 before provider/cache blockers clear, run another Quant PM plus ordinary-user review before any new source-family or factor decision.
