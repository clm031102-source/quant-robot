# CN Stock Round234 Family Rotation And Accounting-Quality Gate - 2026-06-25

## Scope

Machine/task context:

- machine: `office_desktop`;
- task: `factor_validation`;
- branch: `codex/factor-validation-cn-stock-long-cycle-20260618`;
- market/asset: CN stock;
- research-only: no broker, no account reads, no orders, no live trading.

Round234 is a method-optimization and direction-control round, not an alpha promotion round. It closes the Dragon-Tiger line after the size-residual repair failed, then rotates to accounting accruals and cash-flow quality only as a data-readiness/backfill direction.

## Why This Round Was Needed

The previous Dragon-Tiger path had two hard failures:

- Round232 PIT full-sample prescreen found zero direct research leads.
- Round233 size-residual repair also found zero research leads after trying to remove size/style contamination.

Continuing to tune Dragon-Tiger windows, event buckets, or TopN portfolios after those failures would be curve fitting. Round234 therefore hibernates the family and forces a new family decision before any more factor generation.

## Code And Config Changes

Implemented a stricter financial PIT readiness gate:

- `src/quant_robot/ops/tushare_financial_pit_readiness.py`
- `scripts/run_tushare_financial_pit_readiness.py`
- `tests/unit/test_tushare_financial_pit_readiness.py`
- `tests/unit/test_tushare_financial_pit_readiness_cli.py`

The readiness audit now accepts required column groups. This prevents a false pass where local `fina_indicator` data has PIT timing columns and profitability ratios, but does not have the statement fields needed for accruals, asset growth, or cash-flow quality.

New family-rotation configs:

- `configs/family_rotation_candidates_round234_dragon_tiger_hibernation_20260625.json`
- `configs/family_rotation_seed_round234_accounting_quality_backfill_20260625.json`

Startup gate update:

- `configs/factor_mining_startup_cn_stock.json`

The startup gate now points the next allowed direction to:

```text
round235_accounting_quality_pit_statement_backfill_before_preregistration
```

It also blocks:

- Dragon-Tiger continuation after zero residual leads;
- accounting-quality factor generation before required PIT statement fields pass readiness;
- any portfolio grid or promotion before the data gate passes.

## Data Readiness Audit

Command:

```powershell
python scripts\run_tushare_financial_pit_readiness.py `
  --root data\processed `
  --output-dir data\reports\round234_accounting_quality_required_field_readiness_20260625 `
  --required-column-group accounting_accrual_quality:netprofit,ocfps,total_assets `
  --required-column-group asset_growth_quality:total_assets,total_liab,total_cur_assets,total_cur_liab `
  --allow-not-ready
```

Result:

| Metric | Value |
|---|---:|
| Files scanned | 19,084 |
| Financial-like datasets | 9,960 |
| PIT-ready datasets | 9,835 |
| Required column groups | 2 |
| Required column groups passing | 0 |

Blockers:

- `missing_required_financial_column_group:accounting_accrual_quality`
- `missing_required_financial_column_group:asset_growth_quality`

Missing fields:

- `accounting_accrual_quality`: `netprofit`, `total_assets`
- `asset_growth_quality`: `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab`

Interpretation:

Local data is PIT-ready for the existing `fina_indicator` style profitability fields, but not ready for real accounting-quality anomalies that require income statement, balance sheet, and cash-flow statement columns. Therefore Round235 must backfill or map these fields before any factor preregistration.

Forward correction after Round235 implementation:

- The accounting-accrual gate now uses `netprofit`, `n_cashflow_act`, and `total_assets`.
- `ocfps` remains a useful `fina_indicator` field, but it is no longer the required forward gate for statement-based accrual quality.

## Family Rotation Decision

Command:

```powershell
python scripts\run_cn_stock_family_rotation_decision.py `
  --startup-gate data\reports\factor_mining_startup_gate\factor_mining_startup_gate.json `
  --output-dir data\reports\round234_family_rotation_after_dragon_tiger_failure_20260625 `
  --selected-family-id accounting_accruals_cashflow_quality_data_readiness `
  --expected-startup-next-direction round234_hibernate_or_rotate_dragon_tiger_after_size_residual_repair_failure `
  --next-preregistration-direction round235_accounting_quality_pit_statement_backfill_before_preregistration `
  --family-candidates-json configs\family_rotation_candidates_round234_dragon_tiger_hibernation_20260625.json `
  --candidate-plan-seed-json configs\family_rotation_seed_round234_accounting_quality_backfill_20260625.json
```

Result:

| Metric | Value |
|---|---:|
| Families reviewed | 8 |
| Hibernated families | 6 |
| Blocked by data gap | 1 |
| Selected family | 1 |
| Portfolio grid allowed | false |
| Promotion allowed | false |

Selected family:

```text
accounting_accruals_cashflow_quality_data_readiness
```

Next direction:

```text
round235_accounting_quality_pit_statement_backfill_before_preregistration
```

## Decision

No new factor is promotable in Round234.

Dragon-Tiger is hibernated because both the direct PIT event screen and the size-residual repair produced zero research leads. Accounting-quality is selected only because it has stronger public anomaly rationale than another price/flow tuning pass, but it is not allowed to generate factors yet.

The next valid work is Round235:

1. Add or map PIT-safe Tushare income, balance sheet, and cash-flow statement inputs.
2. Re-run required column-group readiness.
3. Only if the required groups pass, pre-register accounting-quality candidates such as accruals quality, cash-flow conversion, asset growth, and working-capital accruals.
4. Keep portfolio grids and promotion disabled until IC/quantile/neutralization/dedup gates pass.

## Verification

Commands run:

```powershell
python -m json.tool configs\factor_mining_startup_cn_stock.json
python -m json.tool configs\family_rotation_candidates_round234_dragon_tiger_hibernation_20260625.json
python -m json.tool configs\family_rotation_seed_round234_accounting_quality_backfill_20260625.json
python scripts\run_factor_mining_startup_gate.py --config configs\factor_mining_startup_cn_stock.json --output-dir data\reports\factor_mining_startup_gate_round235_accounting_quality_backfill_20260625 --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start
python -m unittest tests.unit.test_tushare_financial_pit_readiness tests.unit.test_tushare_financial_pit_readiness_cli tests.unit.test_cn_stock_family_rotation_decision tests.unit.test_cn_stock_family_rotation_decision_cli tests.unit.test_factor_mining_startup_gate_cli
```

Verification result:

- JSON validation passed.
- Startup gate cleared with next direction `round235_accounting_quality_pit_statement_backfill_before_preregistration`.
- Unit tests passed: 21 tests.
