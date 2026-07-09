# CN Stock Round735 LPR Macro Regime State-Conditioned Reference Dedup

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round735 ran true factor-value reference deduplication and exposure reaudit for the two Round734 `gap_widening` LPR-SHIBOR representatives.

This round did not run walk-forward validation, portfolio grids, promotion gates, paper signals, provider downloads, broker connections, account reads, order placement, or final-holdout tuning.

## Implemented Gate

New files:

- `src/quant_robot/ops/lpr_macro_regime_state_conditioned_reference_dedup.py`
- `scripts/run_lpr_macro_regime_state_conditioned_reference_dedup.py`
- `tests/unit/test_lpr_macro_regime_state_conditioned_reference_dedup.py`
- `tests/unit/test_lpr_macro_regime_state_conditioned_reference_dedup_cli.py`

The gate:

- consumes the Round734 factor-value reconstruction smoke;
- rebuilds the LPR-SHIBOR state from repaired local `external_macro_rates`;
- rebuilds residual factor values only for Round734-ready representatives;
- rebuilds public technical reference factors and style exposure controls from local bars and metadata;
- aligns factor values, references, and exposures to the latest LPR state with `available_date <= factor_date`;
- restricts the dedup evidence to the candidate state, currently `gap_widening`;
- blocks candidates with high state-conditioned public-reference redundancy or high size/liquidity/volatility exposure;
- records moderate exposure as a next-step walk-forward challenge, not as promotion evidence;
- allows only the next walk-forward preflight step and keeps portfolio, promotion, paper, and live boundaries blocked.

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

## Real Gate Run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_state_conditioned_reference_dedup.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --smoke data\reports\round734_lpr_macro_regime_factor_value_reconstruction_smoke_20260709\lpr_macro_regime_factor_value_reconstruction_smoke.json --output-dir data\reports\round735_lpr_macro_regime_state_conditioned_reference_dedup_20260709 --analysis-start-date 2024-07-01 --analysis-end-date 2025-12-31 --lookback-days 60 --min-abs-gap-change 0.01 --min-state-dates 20 --min-median-cross-section 100
```

Output: `data/reports/round735_lpr_macro_regime_state_conditioned_reference_dedup_20260709`

Summary:

- Representative candidates: 2
- Rebuilt residual factor-value rows: 2,773,424
- Reference-correlation rows: 18
- Exposure-correlation rows: 10
- State-conditioned reference-dedup pass count: 2
- Blocked candidates: 0
- High-reference candidates: 0
- High-exposure candidates: 0
- Walk-forward preflight allowed next candidates: 2
- Walk-forward preflight run now: 0
- Portfolio-grid allowed candidates: 0
- Promotion-allowed candidates: 0
- Decision blockers: none
- Next direction: `state_conditioned_walk_forward_preflight_after_reference_dedup`

Candidate gate:

| Factor | State | Dates | Median CS | Ref class | Max ref | Ref factor | Exposure class | Max exposure | Exposure | Pass | Requirement |
|---|---|---:|---:|---|---:|---|---|---:|---|---|---|
| `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual` | `gap_widening` | 100 | 4,039 | unique | 0.441 | `donchian_position_20` | moderate_exposure | 0.710 | `realized_vol_20` | yes | walk-forward challenge required for moderate exposure |
| `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual` | `gap_widening` | 100 | 4,039 | unique | 0.689 | `donchian_position_20` | low_exposure | 0.460 | `return_20` | yes | standard walk-forward/cost/final-holdout gates |

Top reference evidence:

- Williams residual vs `donchian_position_20`: 100 observations, mean absolute correlation 0.271, max absolute correlation 0.689, class `unique`.
- Williams residual vs `bollinger_reversal_20`: 100 observations, mean absolute correlation 0.302, max absolute correlation 0.644, class `unique`.
- Anomaly equal-weight residual vs `donchian_position_20`: 100 observations, mean absolute correlation 0.187, max absolute correlation 0.441, class `unique`.

Top exposure evidence:

- Anomaly equal-weight residual vs `realized_vol_20`: 100 observations, mean absolute correlation 0.330, max absolute correlation 0.710, class `moderate_exposure`.
- Anomaly equal-weight residual vs `return_20`: 100 observations, mean absolute correlation 0.370, max absolute correlation 0.690, class `low_exposure`.
- Williams residual vs `return_20`: 100 observations, mean absolute correlation 0.252, max absolute correlation 0.460, class `low_exposure`.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_state_conditioned_reference_dedup.py tests\unit\test_lpr_macro_regime_state_conditioned_reference_dedup_cli.py
```

Result: `3 passed`.

## Decision

Both `gap_widening` representatives pass state-conditioned factor-value reference deduplication and may proceed only to walk-forward preflight.

This is still not alpha, profitability, portfolio, promotion, paper-ready, or live evidence. The next step must run a narrow walk-forward preflight that explicitly challenges the anomaly equal-weight candidate's moderate `realized_vol_20` exposure before any portfolio grid or promotion gate is considered.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
