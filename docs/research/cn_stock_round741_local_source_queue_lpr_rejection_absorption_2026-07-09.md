# CN Stock Round741 Local Source Queue LPR Rejection Absorption

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round741 updated the default local source queue after Round737 rejected the LPR `gap_widening` walk-forward candidates and Round738 closed that path to simple rerun or threshold rescue.

This round did not run a provider download, new factor batch, portfolio grid, promotion gate, paper signal, broker connection, account read, order placement, or final-holdout tuning.

## Change

Updated:

- `src/quant_robot/ops/cn_stock_local_source_queue_audit.py`
- `tests/unit/test_cn_stock_local_source_queue_audit.py`

The `external_macro_lpr_regime` source queue entry is no longer an active no-provider factor source from the old repaired LPR evidence alone.

New default status:

- Source: `external_macro_lpr_regime`
- Status: `source_maintenance_only`
- Evidence still present: true
- Local prescreen allowed: false
- Allowed next action: `new_lpr_macro_interaction_source_gate_only_after_round738_rejection`
- Blocked actions include same LPR gap-widening candidate retry, cost/fold-threshold relaxation, standalone LPR stock rank, portfolio grid before residual prescreen, promotion from source/join smoke, and HK-hold LPR interaction before HK-hold history readiness.

## Real Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round741_local_source_queue_after_lpr_rejection_20260709
```

Output: `data/reports/round741_local_source_queue_after_lpr_rejection_20260709`

Summary:

- Status: `blocked`
- Active source count: 1
- Evidence-ready active source count: 1
- Local-prescreen-ready source count: 1
- No-provider-ready source count: 0
- Provider-ready source count: 1
- Hibernated or closed source count: 11
- Decision blockers: `no_local_no_provider_source_ready`, `report_rc_quota_blocked`
- Local cached prescreen allowed: true
- No-provider factor batch allowed: false
- Provider factor batch allowed: false
- Next action: `wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight`

The only active source remains `analyst_report_revision`; it can support cached local prescreen governance but not a full factor batch while quota blocks provider readiness.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_cn_stock_local_source_queue_audit.py
```

Result: `5 passed`.

## Decision

The repaired LPR source remains useful maintenance evidence, but the default queue must not use it to unlock no-provider factor batches after the Round737/Round738 rejection evidence.

Future LPR work must start from a genuinely new macro-interaction source gate. The current factor-mining route remains `analyst_report_revision` source extension after quota reset, or a separate new PIT-safe source with its own gate.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
