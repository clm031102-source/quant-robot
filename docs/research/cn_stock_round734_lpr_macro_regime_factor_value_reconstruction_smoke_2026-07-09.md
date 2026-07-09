# CN Stock Round734 LPR Macro Regime Factor Value Reconstruction Smoke

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round734 rebuilt residual factor values for the two Round733 `gap_widening` representative candidates and joined them to the LPR-SHIBOR regime state.

This round did not run reference correlations, walk-forward validation, portfolio grids, promotion gates, paper signals, provider downloads, broker connections, account reads, order placement, or final-holdout tuning.

## Implemented Smoke

New files:

- `src/quant_robot/ops/lpr_macro_regime_factor_value_reconstruction_smoke.py`
- `scripts/run_lpr_macro_regime_factor_value_reconstruction_smoke.py`
- `tests/unit/test_lpr_macro_regime_factor_value_reconstruction_smoke.py`
- `tests/unit/test_lpr_macro_regime_factor_value_reconstruction_smoke_cli.py`

The smoke:

- consumes the Round733 reference-dedup routing preflight and rejects non-ready inputs;
- rebuilds the LPR-SHIBOR state from repaired local `external_macro_rates`;
- rebuilds only cluster representatives allowed by Round733;
- reconstructs raw public anomaly and Williams factor values from existing local bars, daily-basic inputs, and stock metadata;
- applies the same industry and size/liquidity/volatility residualization path used by the source prescreens;
- aligns residual factor values to the latest LPR state with `available_date <= factor_date`;
- checks state-date and cross-section coverage inside `gap_widening`;
- allows only the next state-conditioned factor-value reference-dedup step;
- keeps walk-forward, portfolio grids, promotion, and live boundaries blocked.

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

## Real Smoke

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_factor_value_reconstruction_smoke.py --processed-root data\processed\round695_external_feeds_lpr_repaired_20260709 --preflight data\reports\round733_lpr_macro_regime_reference_dedup_preflight_20260709\lpr_macro_regime_reference_dedup_preflight.json --output-dir data\reports\round734_lpr_macro_regime_factor_value_reconstruction_smoke_20260709 --analysis-start-date 2024-07-01 --analysis-end-date 2025-12-31 --lookback-days 60 --min-abs-gap-change 0.01 --min-state-dates 20 --min-median-cross-section 100
```

Output: `data/reports/round734_lpr_macro_regime_factor_value_reconstruction_smoke_20260709`

Summary:

- Representative candidates: 2
- Rebuilt residual factor-value rows: 2,773,424
- Ready candidates: 2
- Blocked candidates: 0
- Walk-forward preflight allowed candidates: 0
- Portfolio-grid allowed candidates: 0
- Promotion-allowed candidates: 0
- Decision blockers: none
- Next direction: `state_conditioned_factor_value_reference_dedup`

Candidate reconstruction:

| Factor | State | Factor rows | State rows | State dates | Median CS | First state date | Last state date |
|---|---|---:|---:|---:|---:|---|---|
| `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual` | `gap_widening` | 1,386,712 | 400,891 | 100 | 4,039 | 2025-02-20 | 2025-09-29 |
| `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual` | `gap_widening` | 1,386,712 | 400,891 | 100 | 4,039 | 2025-02-20 | 2025-09-29 |

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_factor_value_reconstruction_smoke.py tests\unit\test_lpr_macro_regime_factor_value_reconstruction_smoke_cli.py
```

Result: `3 passed`.

## Decision

The two Round733 representatives have enough state-conditioned factor-value coverage to proceed to a true factor-value reference-dedup and exposure reaudit under `gap_widening`.

Do not run walk-forward, portfolio grids, promotion gates, paper signals, or live signals yet. The next allowed step is state-conditioned factor-value reference deduplication against public technical references and exposure controls.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
