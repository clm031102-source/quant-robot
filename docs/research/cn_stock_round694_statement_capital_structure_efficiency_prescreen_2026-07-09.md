# CN Stock Round694 Statement Capital Structure Efficiency Prescreen

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-rotation-round694-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Startup And Gate Evidence

- Startup context: passed for `office_desktop` / `factor_batch`.
- Quant PM startup gate: `ready`, blockers `[]`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`, blockers `[]`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Candidate-plan gate: `research_ready`, 5 active candidates, 9 / 9 complete control areas, no blockers, portfolio grid disabled, promotion disabled.

## Tested Family

Round694 tested the preregistered `statement_capital_structure_efficiency` family:

- `scs_equity_buffer_improvement`
- `scs_liability_to_equity_deleveraging`
- `scs_operating_cashflow_equity_buffer`
- `scs_revenue_to_liability_efficiency`
- `scs_balanced_capital_structure_efficiency`

The family uses PIT statement book-equity buffer, liability-to-equity deleveraging, operating cashflow relative to equity, revenue per liability burden, and a frozen same-date percentile-rank composite. It explicitly avoids direct profitability-quality, working-capital pressure, financial reporting timeliness, PEAD gap reversal, public technical, daily-basic valuation, old northbound, and margin-credit reentry.

## Smoke Checks

Formula smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_formula_smoke.py --root data\processed --output-dir data\reports\round694_statement_capital_structure_efficiency_formula_smoke_20260709
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
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_matrix_label_smoke.py --statement-root data\processed --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\round694_statement_capital_structure_efficiency_matrix_label_smoke_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --min-label-coverage 0.60
```

- Passes: true
- Blockers: `[]`
- Statement rows: 40,523
- Bar rows/assets: 2,441,078 / 959
- Factor value rows: 467,986
- Label aligned rows: 935,943
- Label coverage: 0.999969
- Alignment violation rows: 0
- Signal window: 2015-04-08 to 2025-12-18
- Announcement window used by signals: 2015-04-07 to 2025-12-05

## Residual IC Shape Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py --statement-root data\processed --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --factor-mode statement_capital_structure_efficiency --output-dir data\reports\round694_statement_capital_structure_efficiency_residual_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 8 --min-neutral-rank-ic 0.01 --min-neutral-ic-t-stat 2.0 --min-neutral-retention 0.35
```

Summary:

- Passes: true
- Blockers: `[]`
- Candidates: 5
- Horizons: 5D and 20D
- Tests: 10
- Factor rows: 156,926
- Aligned rows: 313,840
- Bar assets: 959
- Industry neutral observation rows: 2,282
- Size neutral observation rows: 2,290
- Liquidity neutral observation rows: 2,290
- Multiple-testing lead count: 4
- Neutral gate pass count: 0
- Research lead count: 0
- Promotion-allowed candidates: 0

Result rows:

| Candidate | Horizon | Mean IC | ICIR | t-stat | IC positive rate | Quintile spread | Monotonicity | Industry neutral rank IC | Size neutral rank IC | Liquidity neutral rank IC | FDR significant | Research lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `scs_balanced_capital_structure_efficiency` | 20 | -0.0489 | -0.437 | -3.50 | 28.1% | -0.0135 | -0.900 | 0.1274 | -0.0302 | -0.0569 | true | false |
| `scs_balanced_capital_structure_efficiency` | 5 | -0.0421 | -0.321 | -2.56 | 37.5% | -0.0035 | -0.900 | 0.0588 | -0.0354 | -0.0471 | true | false |
| `scs_equity_buffer_improvement` | 5 | -0.0247 | -0.183 | -2.92 | 45.7% | -0.0029 | -0.700 | 0.1134 | -0.0177 | -0.0227 | true | false |
| `scs_liability_to_equity_deleveraging` | 5 | -0.0218 | -0.161 | -2.57 | 44.1% | -0.0022 | -0.800 | 0.1186 | -0.0153 | -0.0166 | true | false |
| `scs_equity_buffer_improvement` | 20 | -0.0154 | -0.116 | -1.84 | 48.4% | -0.0068 | -0.300 | 0.1236 | -0.0050 | -0.0123 | false | false |
| `scs_liability_to_equity_deleveraging` | 20 | -0.0141 | -0.103 | -1.65 | 46.5% | -0.0047 | -0.900 | 0.1262 | -0.0039 | -0.0092 | false | false |
| `scs_operating_cashflow_equity_buffer` | 5 | -0.0139 | -0.093 | -1.58 | 45.3% | 0.0002 | -0.100 | 0.1051 | -0.0080 | -0.0140 | false | false |
| `scs_operating_cashflow_equity_buffer` | 20 | 0.0061 | 0.042 | 0.70 | 52.6% | 0.0011 | -0.200 | 0.1127 | 0.0144 | 0.0115 | false | false |
| `scs_revenue_to_liability_efficiency` | 5 | 0.0028 | 0.019 | 0.33 | 49.0% | -0.0001 | -0.400 | 0.1290 | -0.0044 | 0.0008 | false | false |
| `scs_revenue_to_liability_efficiency` | 20 | -0.0015 | -0.011 | -0.18 | 50.3% | 0.0011 | 0.200 | 0.1439 | -0.0079 | -0.0025 | false | false |

## Decision

Round694 produced four multiple-testing leads, but all are negative raw-direction findings and none passed the neutral gate. The strongest signals fail size and liquidity neutralization in particular, so they are not valid research leads under the current protocol.

Do not flip signs, tune formulas, tune horizons, run portfolio grids, run promotion gates, harvest mixed windows, or read the final holdout for this family. Treat the exact `statement_capital_structure_efficiency` family as rejected as a standalone CN stock factor-mining direction under the current residual IC shape gate.

Next direction from the prescreen packet: `round695_rotate_after_statement_capital_structure_efficiency_residual_ic_shape_failure`.

Generated `data/reports` evidence remains local and uncommitted.
