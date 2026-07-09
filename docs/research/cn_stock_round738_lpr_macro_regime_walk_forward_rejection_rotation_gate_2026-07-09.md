# CN Stock Round738 LPR Macro Regime Walk-Forward Rejection Rotation Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round738 consumed the real Round737 LPR state-conditioned walk-forward validation rejection and converted it into a research-governance rotation gate.

This round did not run a new factor batch, provider download, portfolio grid, promotion gate, paper signal, broker connection, account read, order placement, or final-holdout tuning.

## Implemented Gate

New files:

- `src/quant_robot/ops/lpr_macro_regime_walk_forward_rejection_rotation_gate.py`
- `scripts/run_lpr_macro_regime_walk_forward_rejection_rotation_gate.py`
- `tests/unit/test_lpr_macro_regime_walk_forward_rejection_rotation_gate.py`
- `tests/unit/test_lpr_macro_regime_walk_forward_rejection_rotation_gate_cli.py`

The gate:

- consumes a Round737 `lpr_macro_regime_state_conditioned_walk_forward_validation` JSON report;
- requires the upstream validation to be `rejected`;
- blocks rotation if any LPR candidate is accepted or if statistical reality check, portfolio grid, promotion, or live boundary was unexpectedly opened;
- aggregates candidate and fold rejection reasons into failure families;
- records common failed OOS folds across the frozen LPR candidates;
- verifies whether capacity and exposure challenges were actual blockers;
- retires the same LPR `gap_widening` candidates pending a genuinely new hypothesis;
- forbids rescuing the path by loosening cost, fold-count, final-holdout, portfolio-grid, or promotion gates;
- allows only a new orthogonal source-gate rotation next.

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
.\.venv\Scripts\python.exe scripts\run_lpr_macro_regime_walk_forward_rejection_rotation_gate.py
```

Output: `data/reports/round738_lpr_macro_regime_walk_forward_rejection_rotation_gate_20260709`

Summary:

- Status: `cleared`
- Upstream validation status: `rejected`
- Accepted candidates: 0
- Rejected candidates: 2
- Common failed test folds: `[1]`
- Capacity not blocker: true
- Exposure challenge not blocker: true
- Rotation source gate allowed next: true
- Same LPR candidate retry allowed: false
- Parameter tuning allowed: false
- Statistical reality check allowed next: false
- Portfolio grid allowed: false
- Promotion allowed: false
- Next direction: `rotate_to_non_lpr_orthogonal_family_source_gate`

Candidate rotation table:

| Factor | Status | Accepted folds | Mean test IC | Mean test net LS | Test net total | Capacity dates | Failure families | Retry status |
|---|---|---:|---:|---:|---:|---:|---|---|
| `williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual` | rejected | 1/2 | 0.0164 | 0.0003 | 0.0058 | 0 | IC, cost-adjusted long-short, accepted-fold count | retired pending new hypothesis |
| `public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual` | rejected | 1/2 | 0.0321 | -0.0007 | -0.0143 | 0 | cost-adjusted long-short, accepted-fold count | retired pending new hypothesis |

Failure diagnostics:

- Reason counts: accepted-fold count failures 2, cost-adjusted long-short failures 12, IC failures 4.
- Shared OOS cost failure: true.
- Capacity-limited dates: 0.
- The anomaly candidate's `realized_vol_20` exposure challenge passed in Round737, so exposure challenge failure was not the reason to keep tuning this path.

## Focused Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_lpr_macro_regime_walk_forward_rejection_rotation_gate.py tests\unit\test_lpr_macro_regime_walk_forward_rejection_rotation_gate_cli.py
```

Result: `5 passed`.

## Decision

Round738 clears rotation away from the failed LPR `gap_widening` path.

Do not rerun the same two LPR candidates, reduce cost assumptions, reduce accepted-fold requirements, read final holdout, run portfolio grids, or attempt promotion to rescue this path. The next allowed action is a new orthogonal source gate, or a genuinely new LPR macro-interaction hypothesis that restarts from source gating rather than from walk-forward retry.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
