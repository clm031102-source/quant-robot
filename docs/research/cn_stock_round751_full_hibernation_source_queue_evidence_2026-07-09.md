# CN Stock Round751 Full Hibernation Source Queue Evidence

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round751 completed the evidence hardening pass for the CN stock local source queue. Every non-validation closed, hibernated, or source-maintenance row now requires report evidence instead of relying on default `evidence_present=true`.

This round did not call a provider, download data, run factor IC screens, run portfolio grids, run promotion gates, generate signals, connect to brokers, read accounts, place orders, or read final holdout.

## Change

The following source rows now require matching report evidence:

- `forecast_express_event`
- `share_unlock_pledge`
- `repurchase_contextual_repair`
- `index_rebalance_passive_flow`
- `dragon_tiger_attention`
- `daily_basic_direct`
- `calendar_seasonality`
- `listing_age_board_structural`
- `low_turnover_public_technical_alpha101`

Together with Rounds 749-750, this means the non-validation queue rows now have explicit evidence requirements for:

- active analyst-report revision source accumulation;
- LPR source maintenance;
- closed realized-statement rotations;
- external-feed HK-hold and margin closeouts;
- forecast/express, share-unlock, repurchase/contextual, index-rebalance, dragon-tiger, daily-basic, calendar, listing-age, and public technical/Alpha101/low-turnover closeouts.

Validation-only rows remain control-surface rows and are not treated as active alpha sources.

## Test-Driven Check

Added a source-wide invariant test requiring every non-validation closed/hibernated/source-maintenance source to:

- set `evidence_required=true`;
- report `evidence_present=false` when no matching reports exist;
- keep `local_prescreen_allowed=false`.

Focused green check:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py tests\unit\test_cn_stock_local_source_queue_audit_cli.py -q
```

Result: `12 passed`.

## Real Source Queue Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round751_local_source_queue_full_hibernation_evidence_20260709
```

Result:

- Status: `blocked`
- Source count: 16
- Active source count: 1
- Evidence-ready active source count: 1
- Local-prescreen-ready active source count: 1
- No-provider-ready source count: 0
- Provider-ready source count: 1
- Hibernated or closed source count: 13
- Missing required evidence count: 0
- Blockers:
  - `no_local_no_provider_source_ready`
  - `report_rc_quota_blocked`

Representative matched evidence:

| Source | Evidence matched |
| --- | --- |
| `forecast_express_event` | Round255, Round256, Round268 report dirs |
| `share_unlock_pledge` | Round251 full report dir |
| `repurchase_contextual_repair` | Round248, Round249, Round250, Round303 report dirs |
| `index_rebalance_passive_flow` | Round231 report dir |
| `dragon_tiger_attention` | Round232, Round233, Round234 report dirs |
| `daily_basic_direct` | Round257 and Round258 report dirs |
| `calendar_seasonality` | Round165 cost/capacity report dir |
| `listing_age_board_structural` | Round259 full-core report dir |
| `low_turnover_public_technical_alpha101` | Round116, Round130, Round315, Round333 report dirs |

All matched rows still had `local_prescreen_allowed=false`.

## Readiness Recheck

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --output-dir data\reports\round751_factor_batch_readiness_after_full_hibernation_evidence_20260709 --quota-report-root data\reports --quota-target-date 2026-07-09 --allow-blocked
```

Result:

- Status: `blocked`
- Source queue source count: 16
- Source queue active source count: 1
- Source queue hibernated/closed source count: 13
- Source queue no-provider-ready source count: 0
- Research screen allowed: false
- Portfolio grid allowed: false
- Promotion allowed: false

Blockers remained:

- `provider_quota_preflight_blocked:daily_provider_request_budget_exhausted`
- `source_queue_blocked:no_local_no_provider_source_ready`
- `source_queue_blocked:report_rc_quota_blocked`
- `candidate_plan_gate_blocked:local_source_queue_blocked:no_local_no_provider_source_ready,report_rc_quota_blocked`
- `candidate_plan_gate_blocked:candidate_source_provider_not_allowed:analyst_report_revision`

## Decision

This round improves source-governance rigor but does not create a new factor batch path. The local queue still has no no-provider-ready source. Old hibernated families remain closed unless a future preregistered plan introduces a genuinely new PIT-safe source mechanism rather than parameter, sign, or window tuning.

The only active mining source remains analyst-report revision accumulation after report_rc quota readiness clears.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
