# CN Stock Round710 Office Quota Pack Export

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round710 collected the office desktop analyst-report quota evidence requested by the combined readiness gate. This produced a generated quota pack under `data/reports` for out-of-band use; the generated pack remains outside Git.

This was evidence collection only. It did not run provider downloads, generate new factor formulas, run IC screens, portfolio grids, walk-forward conversion, promotion gates, signal generation, or final-holdout reads.

## Export Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\export_analyst_report_quota_pack.py --report-root data\reports --output-dir data\reports\round710_office_analyst_quota_pack_20260709 --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709
```

Result:

- Status: `exported`.
- Quota pack root: `data\reports\round710_office_analyst_quota_pack_20260709`.
- Machine: `office_desktop`.
- Task: `factor_batch`.
- Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`.
- Exported report count: `11`.
- Skipped report count: `0`.

## Required-Machine Readiness Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --processed-root data\processed --reports-root data\reports --quota-report-root data\reports --quota-report-root data\reports\round710_office_analyst_quota_pack_20260709 --quota-required-pack-machine office_desktop --quota-required-pack-machine highspec_desktop --quota-required-pack-machine laptop --quota-pack-machine-note "highspec_desktop=quota pack not imported on office_desktop round710" --quota-pack-machine-note "laptop=quota pack not imported on office_desktop round710" --output-dir data\reports\round710_factor_batch_readiness_office_quota_pack_20260709 --allow-blocked
```

Result:

- Status: `blocked`.
- Provider quota preflight status: `blocked`.
- Present quota pack machines: `office_desktop`.
- Missing required quota pack machines: `highspec_desktop`, `laptop`.
- Counted provider request windows: `2`.
- Duplicate evidence rows: `2`.
- Quota preflight blockers: `daily_provider_request_budget_exhausted`, `missing_required_quota_pack_machines`.
- Combined next action: `collect_required_quota_pack_evidence`.
- `factor_batch_ready`: `false`.

## Decision

The office side of the quota-pack evidence has been collected locally, but this does not clear provider readiness. The analyst-report path still requires valid highspec desktop and laptop quota-pack evidence, plus the daily `report_rc` budget must no longer be exhausted.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
