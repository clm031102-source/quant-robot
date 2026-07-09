# CN Stock Round729 Local Cached Analyst Prescreen Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round729 split the analyst-report-revision readiness path into two explicit levels:

- Full factor batch readiness remains blocked when provider quota or source-queue readiness is blocked.
- Cached local IC prescreen may run when the active analyst source has local evidence and the candidate plan declares safe prescreen-only boundaries.

Updated:

- `src/quant_robot/ops/cn_stock_local_source_queue_audit.py`
- `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`
- `scripts/run_analyst_report_revision_prescreen.py`
- `tests/unit/test_cn_stock_local_source_queue_audit.py`
- `tests/unit/test_factor_mining_candidate_plan_gate.py`
- `tests/unit/test_analyst_report_revision_prescreen.py`

This did not download provider data, generate new factor formulas, run a portfolio grid, run promotion gates, generate ready signals, run paper simulations, connect to brokers, read accounts, place orders, or read final holdout.

## Change

Source queue now reports cached-prescreen readiness separately from batch readiness:

```json
{
  "local_prescreen_allowed": true,
  "local_prescreen_next_action": "run_cached_local_prescreen_then_wait_for_report_rc_quota_reset"
}
```

Candidate-plan gate now propagates this to candidate rows:

```json
{
  "source_queue_allowed": false,
  "local_prescreen_allowed": true
}
```

The analyst prescreen CLI now accepts:

```powershell
--local-prescreen-candidate-plan-gate <factor_mining_candidate_plan_gate.json>
```

That gate allows cached IC prescreen only. It still rejects portfolio grids, promotion, and live boundary use.

## Red Tests

Added focused tests for:

- Source queue remains blocked for full factor batch when quota blocks provider access, while `local_prescreen_allowed=true` if local analyst evidence exists.
- Candidate-plan gate remains blocked for full research screen, but exposes `local_prescreen_allowed=true` for all four analyst revision candidates.
- Candidate local-prescreen validation accepts a blocked full-batch candidate gate only when cached-source prescreen is explicitly allowed.
- Analyst prescreen CLI can run from a local-prescreen gate without a full ready batch packet.

## Real Gate Rebuild

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json --output-dir data\reports\round729_factor_batch_readiness_local_prescreen_gate_20260709 --quota-report-root data\reports --quota-target-date 2026-07-09 --allow-blocked
```

Result:

- Full readiness status: `blocked`.
- Full readiness blockers:
  - `provider_quota_preflight_blocked:daily_provider_request_budget_exhausted`
  - `source_queue_blocked:no_local_no_provider_source_ready`
  - `source_queue_blocked:report_rc_quota_blocked`
  - `candidate_plan_gate_blocked:local_source_queue_blocked:no_local_no_provider_source_ready,report_rc_quota_blocked`
  - `candidate_plan_gate_blocked:candidate_source_provider_not_allowed:analyst_report_revision`
- Source queue: `local_prescreen_allowed=true`.
- Candidate gate: `local_prescreen_allowed=true`.
- Local-prescreen candidate count: 4.
- Portfolio grid allowed: `false`.
- Promotion allowed: `false`.

## Real Cached Prescreen

Command used the existing Jan-Jun 2024 analyst cache and long-cycle bars, plus the new local-prescreen candidate gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --report-root data\processed\round507_analyst_report_revision_cache_202404_20260707 --report-root data\processed\round700_analyst_report_revision_cache_202405_20260709 --report-root data\processed\round701_analyst_report_revision_cache_202406_20260709 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round729_analyst_report_revision_jan_jun_local_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 30 --min-ic-observations 8 --local-prescreen-candidate-plan-gate data\reports\round729_factor_batch_readiness_local_prescreen_gate_20260709\candidate_plan_gate\factor_mining_candidate_plan_gate.json
```

Result summary:

- Bar rows: 10,785,537.
- Bar assets: 5,707.
- Report rows: 10,509.
- Report assets: 2,226.
- Factor rows: 24,781.
- Aligned rows: 49,562.
- Candidate count: 4.
- Factor/horizon tests: 8.
- Neutral gate pass count: 2.
- Multiple-testing lead count: 4.
- Year coverage pass count: 0.
- Research lead count: 0.
- Promotion allowed candidates: 0.
- Next direction: `rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads`.

The strongest displayed row was `analyst_target_upside_60` at horizon 5:

- Mean Spearman IC: 0.1511.
- ICIR: 0.5775.
- FDR significant: `true`.
- Mean industry-neutral rank IC: 0.4182.
- Mean size-neutral rank IC: 0.1146.
- IC year count: 1.
- Research lead: `false`.
- Promotion allowed: `false`.
- Blockers include `ic_year_coverage_below_gate` and later walk-forward/cost/capacity/regime gates.

## Decision

Use the new local-prescreen gate only to re-run cached analyst IC prescreens while provider quota is blocked. Do not treat local-prescreen permission as full factor-batch readiness.

The analyst-report-revision family still has no promotable research lead from Jan-Jun 2024 cache. The useful next action is either to wait for report_rc quota reset and extend source history, or rotate to another PIT-safe source. No portfolio grid or promotion should run from this evidence.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
