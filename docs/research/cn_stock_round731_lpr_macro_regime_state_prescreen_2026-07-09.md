# CN Stock Round731 LPR Macro Regime State Prescreen

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round731 added and ran a narrow state prescreen for the Round730 LPR macro-rate candidate.

This round did not run a portfolio grid, promotion gate, paper simulation, live signal, provider download, broker connection, account read, order placement, or final-holdout tuning.

The candidate remains a regime-control input only. It is not a standalone stock rank or profitability claim.

## Implemented Gate

New files:

- `src/quant_robot/ops/lpr_macro_regime_state_prescreen.py`
- `scripts/run_lpr_macro_regime_state_prescreen.py`
- `tests/unit/test_lpr_macro_regime_state_prescreen.py`
- `tests/unit/test_lpr_macro_regime_state_prescreen_cli.py`

The prescreen:

- validates the current factor-batch readiness gate before reading local processed data;
- reads local `external_macro_rates` from `data/processed/round695_external_feeds_lpr_repaired_20260709`;
- uses `signal_date = available_date`;
- computes `lpr_shibor_3m_gap = lpr_1y - shibor_3m`;
- computes the 60 available-observation change of that gap;
- classifies states as `gap_widening`, `gap_narrowing`, `gap_flat`, or `insufficient_lookback`;
- excludes 2026 final holdout by default;
- keeps standalone alpha, portfolio grids, promotion, and live boundary blocked;
- allows only the next residual-IC pairing step when the state is non-degenerate.

## Startup Gates

Quant PM startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709
```

Result: `status=ready`, `primary_market=CN_ETF`, blockers `[]`.

Factor-mining startup gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-source-readiness-round695-20260709 --market CN --asset-type stock --commits-allowed --confirm-start
```

Result: `status=cleared`, startup blockers `[]`, pushes disabled.

## Real Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_state_prescreen.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --readiness-gate data\reports\round730_lpr_macro_regime_factor_batch_readiness_after_state_check_20260709\factor_batch_readiness_gate.json --candidate-plan configs\factor_mining_candidate_plan_round730_lpr_macro_regime_control_20260709.json --output-dir data\reports\round731_lpr_macro_regime_state_prescreen_20260709 --analysis-start-date 2024-07-01 --analysis-end-date 2025-12-31 --lookback-days 60 --min-abs-gap-change 0.01 --min-state-dates 5 --min-nonzero-gap-changes 20
```

Output: `data/reports/round731_lpr_macro_regime_state_prescreen_20260709`

Summary:

- Active candidates: 1
- Inactive candidates: 2
- State rows: 343
- State count: 3
- Directional state count: 2
- Non-zero 60-observation gap changes: 276
- Ready regime-control candidates: 1
- Decision blockers: none
- Portfolio-grid allowed candidates: 0
- Promotion-allowed candidates: 0
- PIT available-date violations: 0
- Raw-date not-before-signal violations: 0
- Final holdout included: false
- Live boundary allowed: false

State distribution:

| State | Dates | Share | First available | Last available |
|---|---:|---:|---|---|
| `gap_narrowing` | 177 | 51.6% | 2024-09-27 | 2025-12-31 |
| `gap_widening` | 99 | 28.9% | 2025-02-20 | 2025-09-29 |
| `gap_flat` | 7 | 2.0% | 2025-02-28 | 2025-09-30 |
| `insufficient_lookback` | 60 | 17.5% | 2024-07-02 | 2024-09-26 |

Candidate result:

- `lpr_shibor_credit_gap_regime_60`: `state_ready_for_regime_control=true`, blockers `[]`.
- `lpr_term_premium_easing_regime_60`: remains inactive because term premium is state-degenerate.
- `hk_hold_stability_x_lpr_easing_regime_60`: remains inactive because hk-hold history is below the minimum.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_state_prescreen.py tests\unit\test_lpr_macro_regime_state_prescreen_cli.py
```

Result: `4 passed`.

## Decision

`lpr_shibor_credit_gap_regime_60` is usable as a non-degenerate macro regime-control state for the next local residual-IC pairing prescreen.

This is source/state readiness only. It is not evidence of stock alpha, profitability, portfolio readiness, or promotion.

Next allowed step: pair the LPR-SHIBOR gap state with a pre-registered stock factor and measure residual IC by regime, with industry/size/liquidity controls, reference deduplication, multiple-testing accounting, walk-forward, cost/capacity, and final-holdout rules still required before any stronger claim.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
