# CN Stock Industry/Style Exposure Audit Round203

- Date: 2026-06-23
- Scope: CN stock factor mining pre-portfolio controls
- Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Why

Previous rounds had industry-neutral or residual checks scattered across family-specific scripts. That let some candidates reach IC or TopN thinking before a universal industry/style decomposition was attached. Round203 promotes this into a reusable gate.

## What Changed

- Added `src/quant_robot/ops/industry_style_exposure_audit.py`.
- Added `scripts/run_industry_style_exposure_audit.py`.
- Added unit and CLI tests for:
  - a candidate whose residual IC survives industry and style controls,
  - missing style/industry coverage rejection,
  - JSON/Markdown/CSV output writing.
- Startup protocol now requires:
  - `industry_style_exposure_audit_before_portfolio_grid`
  - `industry_r2_and_style_correlation_report_required`
  - `residual_factor_matrix_required_before_portfolio_grid`
  - `style_decomposition_size_value_lowvol_momentum_liquidity_required`
- Startup confirmations now include:
  - `industry_style_exposure_audit_confirmed`
  - `industry_r2_and_style_correlation_report_confirmed`
  - `residual_factor_matrix_before_portfolio_grid_confirmed`
  - `raw_topn_without_residual_audit_rejected`

## Outputs

The audit writes:

- `industry_style_exposure_audit.json`
- `industry_style_exposure_audit.md`
- `factor_summary.csv`
- `industry_date_rows.csv`
- `style_exposure_rows.csv`
- `residual_factor_rows.csv`

The standard candidate review must attach the audit packet before any portfolio grid. Raw TopN returns without `residual_factor_rows.csv` or an explicit residual-failure blocker are not promotable evidence.

## Quality Gate Update

These controls are now implemented as reusable process controls:

- `industry_exposure_report`
- `style_exposure_report`
- `size_value_lowvol_momentum_liquidity_decomposition`
- `neutralized_factor_matrix_or_residual_option`

`financial_revision_announcement_handling` is also upgraded to implemented process-control status because the PIT timing audit and signal-date filter preserve distinct revision `ann_date` rows, block exact duplicate financial keys, and require later signal dates. The current real Round95 sample had no observed revision groups, so this remains timing-control evidence only.

## Non-Claims

- This is not a profitable factor.
- This is not portfolio promotion evidence.
- This does not waive tradeability, cost, capacity, regime, walk-forward, final-holdout, or statistical reality-check gates.

## Verification

Commands run:

```powershell
python -m unittest tests.unit.test_industry_style_exposure_audit tests.unit.test_industry_style_exposure_audit_cli tests.unit.test_financial_pit_signal_date_filter
python -m unittest tests.unit.test_factor_mining_startup_gate
python -m py_compile src\quant_robot\ops\factor_mining_startup.py src\quant_robot\ops\industry_style_exposure_audit.py scripts\run_industry_style_exposure_audit.py
```

Observed result: all listed tests passed.
