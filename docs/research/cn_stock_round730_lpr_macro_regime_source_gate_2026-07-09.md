# CN Stock Round730 LPR Macro Regime Source Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round730 advanced the repaired LPR macro-rate path from source-quality evidence to a gated research-screen candidate path.

This round did not run a portfolio grid, promotion gate, paper simulation, live signal, provider download, broker connection, account read, order placement, or final-holdout read.

## Source Evidence

Existing repaired source audit:

- Path: `data/reports/round695_external_feed_lpr_repaired_coverage_audit_20260709/external_feed_coverage_audit.json`
- `external_macro_rates` status: `pass`
- LPR non-null ratio: `1.0`
- LPR 1Y non-null rows: `340`
- LPR 5Y non-null rows: `340`
- Unique macro observation dates: `340`
- Window: `2024-07-01` to `2025-12-31`

Round730 PIT join smoke:

- Output: `data/reports/round730_lpr_regime_join_smoke_20260709`
- Seeds tested: 3
- Pass count: 2
- Insufficient-history count: 1
- Fail count: 0
- Available-date violations: 0
- Same-day/future raw-date violations: 0
- Joined rows: 1,995,559

Passing seeds:

- `lpr_term_premium_easing_regime_60`
- `lpr_shibor_credit_gap_regime_60`

State-distribution check after the PIT join smoke found that `lpr_term_premium_easing_regime_60` is degenerate in the repaired sample:

- `lpr_1y` unique values: 4.
- `lpr_5y` unique values: 4.
- `lpr_5y - lpr_1y` unique values: 1.
- Term premium min/max: `0.5` / `0.5`.
- Non-zero 60-day term-premium changes: 0.

The term-premium seed is therefore documented as `blocked_by_state_degenerate`, not active for discovery.

Other blocked seed:

- `hk_hold_stability_x_lpr_easing_regime_60`
- Reason: only 40 `external_hk_hold` observation dates versus the 60-day minimum.

## Code And Config Changes

Updated:

- `src/quant_robot/ops/cn_stock_local_source_queue_audit.py`
- `configs/china_market_regime_control_policy_cn_stock.json`
- `configs/factor_mining_candidate_plan_round730_lpr_macro_regime_control_20260709.json`
- `tests/unit/test_cn_stock_local_source_queue_audit.py`
- `tests/unit/test_factor_mining_candidate_plan_gate.py`
- `tests/unit/test_china_market_regime_control_gate.py`

Source queue change:

- Added `external_macro_lpr_regime` as a conditional active source.
- It becomes `active_source_accumulation` only when both repaired processed evidence and coverage-audit evidence exist.
- It is `provider_required=false`.
- It blocks standalone LPR stock ranking, portfolio grids before residual prescreen, promotion from source/join smoke, and hk_hold×LPR interaction before hk_hold history is ready.
- Provider quota blocks on analyst report revision are now warnings when a no-provider source is ready, not blockers for the whole source queue.

Regime-control policy change:

- `lpr_1y` and `lpr_5y` moved from `blocked_fields` to `usable_fields` for `policy_liquidity_regime`.
- `standalone_alpha_claim_allowed` remains `false`.
- Real gate after the change reports `blocked_fields_count=0` and `passes=true`.

Candidate plan:

- New config: `configs/factor_mining_candidate_plan_round730_lpr_macro_regime_control_20260709.json`
- Active candidates: 1
- Inactive candidates: 2, blocked by state degeneracy and coverage.
- Portfolio grid allowed: `false`
- Promotion allowed: `false`

## Real Gates

Source queue:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_local_source_queue_audit.py --processed-root data\processed --reports-root data\reports --output-dir data\reports\round730_local_source_queue_lpr_active_20260709
```

Result:

- Status: `cleared`
- Active sources: 2
- Evidence-ready active sources: 2
- No-provider-ready sources: 1
- Provider-ready sources: 1
- Blockers: none
- Warnings: `report_rc_quota_blocked`
- Next action: `run_no_provider_factor_batch_from_ready_local_source`

Candidate-plan gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round730_lpr_macro_regime_control_20260709.json --local-source-queue-audit data\reports\round730_local_source_queue_lpr_active_20260709\cn_stock_local_source_queue_audit.json --output-dir data\reports\round730_lpr_macro_regime_candidate_plan_gate_20260709 --allow-blocked
```

Initial result:

- Status: `research_ready`
- Candidate-plan gate cleared: `true`
- Research screen allowed: `true`
- Local prescreen allowed: `true`
- Portfolio grid allowed: `false`
- Promotion allowed: `false`
- Active candidates: 2
- Inactive candidates: 1

After the state-distribution check, the candidate gate was rerun to:

- Output: `data/reports/round730_lpr_macro_regime_candidate_plan_gate_after_state_check_20260709`
- Active candidates: 1
- Inactive candidates: 2
- Local-prescreen candidate count: 1

No-provider factor-batch readiness:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_batch_readiness_gate.py --candidate-plan configs\factor_mining_candidate_plan_round730_lpr_macro_regime_control_20260709.json --output-dir data\reports\round730_lpr_macro_regime_factor_batch_readiness_20260709 --allow-blocked
```

Initial result:

- Status: `ready`
- Factor batch ready: `true`
- Research screen allowed: `true`
- Portfolio grid allowed: `false`
- Promotion allowed: `false`
- Provider quota preflight status: `not_provided`
- Next action: `run_frozen_candidate_prescreen`

After the state-distribution check, the readiness gate was rerun to:

- Output: `data/reports/round730_lpr_macro_regime_factor_batch_readiness_after_state_check_20260709`
- Status: `ready`
- Research screen allowed: `true`
- Portfolio grid allowed: `false`
- Promotion allowed: `false`

## Decision

The LPR macro-rate source is ready for a dedicated residual/regime-control prescreen, but only for `lpr_shibor_credit_gap_regime_60`. The term-premium seed is inactive because it has no state variation in the repaired sample. The current repo does not have a direct LPR macro residual prescreen; the closest old regime-temperature prescreen depends on daily-basic factor inputs and should not be reused blindly.

Next implementation should build a narrow LPR macro regime residual prescreen that:

- uses only `available_date <= signal_date`;
- screens `lpr_shibor_credit_gap_regime_60`;
- keeps `lpr_term_premium_easing_regime_60` blocked unless future source evidence shows non-degenerate term-structure variation;
- treats the factors as regime controls or stratification states, not standalone stock ranks;
- measures state coverage and residual IC interaction against pre-registered stock factors;
- keeps hk_hold×LPR blocked until hk_hold history coverage reaches the minimum;
- keeps portfolio grids and promotion blocked until residual, walk-forward, cost/capacity, regime, and source-performance gates pass.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
