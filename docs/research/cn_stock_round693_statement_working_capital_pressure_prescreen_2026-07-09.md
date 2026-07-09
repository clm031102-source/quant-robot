# CN Stock Round693 Statement Working Capital Pressure Prescreen

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-statement-working-capital-pressure-round693-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Startup And Gate Evidence

- Startup context: passed for `office_desktop` / `factor_batch`.
- Quant PM startup gate: `ready`, blockers `[]`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Candidate-plan gate: `research_ready`, 5 active candidates, 9 / 9 complete control areas, no blockers, portfolio grid disabled, promotion disabled.

## Tested Family

Round693 tested the preregistered `statement_working_capital_pressure` family:

- `swcp_cash_current_liability_improvement`
- `swcp_operating_working_capital_release`
- `swcp_inventory_receivable_efficiency_improvement`
- `swcp_free_cashflow_liability_buffer`
- `swcp_balanced_cash_working_capital_pressure`

The family is based on PIT statement fields for cash-current-liability coverage, operating working-capital release, inventory/receivable intensity, free-cashflow liability buffers, and an equal-weight percentile-rank composite. It is not a same-family rerun of financial reporting timeliness, PEAD gap reversal, realized profitability revision, cash-conversion event drift, or public technical factors.

## Smoke Checks

Formula smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_formula_smoke.py --root data\processed --output-dir data\reports\round693_statement_working_capital_pressure_formula_smoke_20260709
```

- Passes: true
- Blockers: `[]`
- Source files: 2,853
- Statement rows before dedup: 40,665
- Statement rows after dedup: 40,523
- Duplicate statement key rows: 142
- Unique assets: 959
- Formula count: 13
- Formulas with values: 13

Matrix-label smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_matrix_label_smoke.py --statement-root data\processed --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\round693_statement_working_capital_pressure_matrix_label_smoke_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --min-label-coverage 0.60
```

- Passes: true
- Blockers: `[]`
- Statement rows: 40,523
- Bar rows/assets: 2,441,078 / 959
- Factor value rows: 458,246
- Label aligned rows: 916,467
- Label coverage: 0.999973
- Alignment violation rows: 0
- Signal window: 2015-04-08 to 2025-12-18
- Announcement window used by signals: 2015-04-07 to 2025-12-05

## Residual IC Shape Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py --statement-root data\processed --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --factor-mode statement_working_capital_pressure --output-dir data\reports\round693_statement_working_capital_pressure_residual_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 8 --min-neutral-rank-ic 0.01 --min-neutral-ic-t-stat 2.0 --min-neutral-retention 0.35
```

Summary:

- Passes: true
- Blockers: `[]`
- Candidates: 5
- Horizons: 5D and 20D
- Tests: 10
- Factor rows: 41,590
- Aligned rows: 83,180
- Bar assets: 959
- Industry neutral observation rows: 620
- Size neutral observation rows: 620
- Liquidity neutral observation rows: 620
- Multiple-testing lead count: 0
- Neutral gate pass count: 0
- Research lead count: 0
- Promotion-allowed candidates: 0

Result rows:

| Candidate | Horizon | Mean IC | ICIR | t-stat | IC positive rate | Quintile spread | Monotonicity | Industry neutral rank IC | Size neutral rank IC | Liquidity neutral rank IC | FDR significant | Research lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `swcp_free_cashflow_liability_buffer` | 20 | -0.0433 | -0.327 | -2.58 | 38.7% | -0.0144 | -0.900 | 0.2141 | -0.0307 | -0.0424 | false | false |
| `swcp_inventory_receivable_efficiency_improvement` | 5 | -0.0366 | -0.316 | -2.49 | 35.5% | -0.0027 | -1.000 | 0.1609 | -0.0353 | -0.0378 | false | false |
| `swcp_balanced_cash_working_capital_pressure` | 20 | -0.0207 | -0.167 | -1.32 | 50.0% | -0.0099 | -0.700 | 0.1945 | -0.0139 | -0.0181 | false | false |
| `swcp_free_cashflow_liability_buffer` | 5 | -0.0130 | -0.094 | -0.74 | 45.2% | -0.0025 | -0.700 | 0.1407 | -0.0068 | -0.0116 | false | false |
| `swcp_cash_current_liability_improvement` | 5 | -0.0129 | -0.103 | -0.81 | 40.3% | -0.0026 | -0.800 | 0.1014 | -0.0142 | -0.0082 | false | false |
| `swcp_balanced_cash_working_capital_pressure` | 5 | -0.0126 | -0.109 | -0.86 | 51.6% | -0.0014 | -0.300 | 0.1483 | -0.0114 | -0.0099 | false | false |
| `swcp_operating_working_capital_release` | 5 | 0.0113 | 0.096 | 0.75 | 54.8% | 0.0042 | 0.700 | 0.1984 | 0.0079 | 0.0180 | false | false |
| `swcp_inventory_receivable_efficiency_improvement` | 20 | -0.0108 | -0.082 | -0.65 | 40.3% | 0.0044 | 0.300 | 0.1823 | -0.0127 | -0.0089 | false | false |
| `swcp_operating_working_capital_release` | 20 | 0.0098 | 0.066 | 0.52 | 54.8% | 0.0050 | 0.400 | 0.1898 | 0.0092 | 0.0185 | false | false |
| `swcp_cash_current_liability_improvement` | 20 | -0.0071 | -0.056 | -0.44 | 58.1% | -0.0020 | -0.800 | 0.1119 | -0.0042 | -0.0075 | false | false |

## Decision

Round693 produced no research lead and no promotion candidate. The exact `statement_working_capital_pressure` family is rejected as a standalone CN stock factor-mining direction under the current residual IC shape gate.

Do not run portfolio grids, promotion gates, sign flips, lag/window/horizon tuning, mixed-window harvesting, or final-holdout reads for this family. Future work should rotate to a genuinely orthogonal source or hypothesis rather than reusing these working-capital pressure transforms.

Next direction from the prescreen packet: `round694_rotate_after_statement_working_capital_pressure_residual_ic_shape_failure`.

Generated `data/reports` evidence remains local and uncommitted.
