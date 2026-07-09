# CN Stock Round692 PEAD Gap Reversal Source Repair Prescreen

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-pead-gap-reversal-source-repair-round692-20260709`

Scope: implement the statement-source adapter required for the Round692 PEAD gap-reversal source-repair audit, then run matrix/label smoke and residual IC prescreen on the five preregistered 5D `stmt_pead_*` candidates. No formula-grid expansion, portfolio grid, walk-forward, promotion gate, live-trading work, or 2026 final-holdout read occurred.

## Implementation Evidence

Code path:

- Added a PEAD statement-source adapter that converts local `processed/financial_statement_inputs` rows into the existing PIT PEAD financial frame.
- Added `financial_input_kind="statement"` support to the gap-reversal matrix smoke and residual prescreen APIs and CLI scripts.
- Added statement-source tests covering adapter output, matrix smoke, residual prescreen, and CLI wiring.
- Preserved the default `fina_indicator` path for existing Round223 tests.

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_financial_pit_post_announcement_gap_reversal_residual_prescreen.py tests\unit\test_financial_pit_post_announcement_gap_reversal_matrix_label_smoke.py tests\unit\test_financial_pit_post_announcement_gap_reversal_statement_source.py -q
```

Result:

```text
9 passed
```

## Matrix And Label Smoke

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke.py --financial-root data\processed --financial-input-kind statement --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --preregistration-json configs\factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json --candidate-plan-gate-json data\reports\round692_pead_gap_reversal_source_repair_candidate_plan_gate_20260709\factor_mining_candidate_plan_gate.json --output-dir data\reports\round692_pead_gap_reversal_source_repair_matrix_label_smoke_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --execution-lag 1 --min-label-coverage 0.60
```

Result:

| Metric | Value |
| --- | ---: |
| Passes | true |
| Active candidates | 5 |
| Unknown active candidates | 0 |
| Financial rows | 39,704 |
| Financial assets | 959 |
| Bar rows | 2,339,772 |
| Factor value rows | 191,451 |
| Label aligned rows | 191,451 |
| Label coverage | 100.00% |
| Alignment violations | 0 |
| Min signal date | 2015-04-08 |
| Max signal date | 2025-11-11 |
| Max factor date | 2025-11-12 |
| Max label date | 2025-12-23 |
| Final holdout included | false |

## Residual IC Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_pit_post_announcement_gap_reversal_residual_prescreen.py --financial-root data\processed --financial-input-kind statement --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --preregistration-json configs\factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json --candidate-plan-gate-json data\reports\round692_pead_gap_reversal_source_repair_candidate_plan_gate_20260709\factor_mining_candidate_plan_gate.json --stock-basic data\processed\cn_stock_metadata --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --output-dir data\reports\round692_pead_gap_reversal_source_repair_residual_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --execution-lag 1 --min-cross-section 30 --min-ic-observations 8 --min-neutral-rank-ic 0.01 --min-neutral-ic-t-stat 2.0 --min-neutral-retention 0.35
```

Result:

| Metric | Value |
| --- | ---: |
| Passes | true |
| Candidate count | 5 |
| Test count | 5 |
| Factor rows | 191,451 |
| Aligned rows | 191,451 |
| Label rows | 2,334,018 |
| Multiple-testing lead count | 4 |
| Neutral-gate pass count | 0 |
| Research lead count | 0 |
| Reference dedup pass count | 5 |
| Promotion allowed candidates | 0 |
| Bar assets | 959 |
| Reference factor rows | 324,749 |
| Final holdout included | false |

## Candidate Results

| Candidate | IC | ICIR | t | Pos IC | QSpread | Mono | IndNeuIC | SizeNeuIC | LiqNeuIC | FDR | Lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `stmt_pead_gap_overreaction_reversal_volume_confirmed_1_5` | -0.0303 | -0.176 | -2.99 | 43.1% | -0.0053 | -0.900 | 0.1452 | -0.0311 | -0.0285 | yes | no |
| `stmt_pead_gap_overreaction_reversal_1_5` | -0.0275 | -0.161 | -2.73 | 43.4% | -0.0051 | -0.900 | 0.1573 | -0.0271 | -0.0256 | yes | no |
| `stmt_pead_gap_overreaction_reversal_size_neutral_candidate_1_5` | -0.0272 | -0.160 | -2.71 | 44.4% | -0.0051 | -0.900 | 0.1563 | -0.0274 | -0.0256 | yes | no |
| `stmt_pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` | -0.0214 | -0.126 | -2.14 | 44.1% | -0.0045 | -0.900 | 0.1707 | -0.0212 | -0.0197 | yes | no |
| `stmt_pead_gap_overreaction_reversal_quality_conditioned_1_5` | -0.0114 | -0.081 | -1.28 | 50.0% | -0.0026 | -0.500 | 0.1249 | -0.0114 | -0.0118 | no | no |

The expanded source produced statistically significant negative raw IC for four candidates. Industry-neutral rank IC was positive, but size-neutral and liquidity-neutral IC remained negative, quantile spreads were negative, monotonicity was weak or inverted, and the neutral gate accepted zero candidates.

## Data And Safety Notes

- Manifest warnings carried forward: `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars`.
- Generated artifacts under `data\reports\round692_pead_gap_reversal_source_repair_matrix_label_smoke_20260709` and `data\reports\round692_pead_gap_reversal_source_repair_residual_prescreen_20260709` are ignored by Git.
- No broker connection, account read, order placement, automatic trading, paper-ready package, or 2026 final-holdout read occurred.

## Decision

Do not promote any Round692 `pead_gap_reversal_statement_source_repair` candidate. The source expansion repaired coverage but inverted or weakened the apparent Round223 edge after style and neutral gates. The family should not move to portfolio walk-forward or promotion from this result.

Next direction: rotate away from PEAD gap-reversal source repair unless a future preregistered audit explicitly tests the opposite economic sign as a separate hypothesis. No sign flip or parameter/window harvesting is allowed from this Round692 result.
