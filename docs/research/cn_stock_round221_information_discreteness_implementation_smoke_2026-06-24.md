# CN Stock Round221 Information Discreteness Implementation And Smoke

Date: 2026-06-24

Scope: CN A-share stock cross-sectional factor research. This is not ETF rotation, not live trading, and not a portfolio promotion.

## What Changed

Implemented the Round221 `information_discreteness_path_quality` family as a registered factor source and residual-prescreen path:

- `src/quant_robot/factors/information_discreteness.py`
- `src/quant_robot/ops/information_discreteness_residual_prescreen.py`
- `scripts/run_information_discreteness_residual_prescreen.py`
- `configs/family_rotation_seed_round221_information_discreteness_20260624.json`
- `configs/family_rotation_candidates_round221_information_discreteness_20260624.json`
- `docs/research/cn_stock_round221_information_discreteness_preregistration_2026-06-24.md`

The family is now accepted by:

- `ResearchPipelineConfig.factor_source="information_discreteness"`
- project factor registry audit;
- startup gate repeatable mining protocol;
- standalone residual/reference/exposure prescreen CLI.

## Candidate Names

- `fip_smooth_momentum_quality_60_20`
- `fip_smooth_momentum_skip5_60`
- `fip_continuous_accumulation_low_jump_20_60`
- `fip_discrete_jump_reversal_20_5`
- `fip_smooth_pullback_resilience_60_20`
- `fip_volume_confirmed_smooth_trend_20_60`

## Verification

- Red test first: `python -m unittest tests.unit.test_information_discreteness_factors` failed with missing module.
- Green factor tests: `python -m unittest tests.unit.test_information_discreteness_factors` passed, 6 tests.
- Red registration tests failed before pipeline/audit registration.
- Green registration tests passed after wiring `information_discreteness` into the pipeline and project audit.
- Red sharded test failed before CLI support.
- Green sharded test passed after wiring the Round220 streaming shard collector into Round221.
- Related regression:

`python -m unittest tests.unit.test_information_discreteness_factors tests.unit.test_information_discreteness_residual_prescreen tests.unit.test_information_discreteness_residual_prescreen_cli tests.unit.test_research_pipeline.ResearchPipelineTests.test_pipeline_computes_only_requested_information_discreteness_factor tests.unit.test_project_audit.ProjectAuditTests.test_audit_accepts_registered_information_discreteness_factor_source tests.unit.test_factor_mining_startup_gate_cli.FactorMiningStartupGateCliTests.test_default_cn_stock_config_is_runnable`

Result: 14 tests OK.

- Compile:

`python -m py_compile src\quant_robot\factors\information_discreteness.py src\quant_robot\ops\information_discreteness_residual_prescreen.py scripts\run_information_discreteness_residual_prescreen.py`

Result: OK.

- JSON validity:

`configs/factor_mining_startup_cn_stock.json`, `configs/family_rotation_seed_round221_information_discreteness_20260624.json`, and `configs/family_rotation_candidates_round221_information_discreteness_20260624.json` passed `python -m json.tool`.

## Startup Gate

Output:

`data/reports/factor_mining_startup_gate_round221_information_discreteness_20260624/`

Status:

- startup gate cleared;
- current branch: `codex/factor-validation-cn-stock-long-cycle-20260618`;
- machine/task: `office_desktop` / `factor_validation`;
- scope: CN stock, ETF rotation rejected;
- next direction after this report should be full long-cycle sharded residual prescreen.

## Real-Data Smoke

First smoke command:

`python scripts\run_information_discreteness_residual_prescreen.py --analysis-start-date 2024-01-01 --analysis-end-date 2024-03-31 --candidate-factor-name fip_smooth_momentum_quality_60_20 ...`

Result:

- factor rows: 0;
- root cause: 60/65-day lookback family with a short Jan-Mar analysis window and no padding.
- conclusion: this is a process failure signal, not factor evidence.

Sharded warmup smoke command:

`python scripts\run_information_discreteness_residual_prescreen.py --sharded --analysis-start-date 2024-04-01 --analysis-end-date 2024-06-30 --candidate-factor-name fip_smooth_momentum_quality_60_20 --lookback-calendar-days 120 --forward-calendar-days 30 --sample-every-n-dates 10 --min-cross-section 10 --min-ic-observations 3 --min-signal-date-amount 1000000 --min-industry-neutral-icir -99 --min-residual-icir -99`

Output:

`data/reports/information_discreteness_residual_prescreen_round221_sharded_smoke_20260624/`

Data:

- signal window: 2024-04-01 through 2024-06-30;
- loaded window: 2023-12-03 through 2024-07-30;
- sharding: enabled, streaming summary true;
- bar rows: 315,484;
- factor rows: 251,153;
- industry-neutral rows: 248,435;
- residual rows: 248,435;
- label rows: 315,295;
- reference factor count: 9.

Smoke result for `fip_smooth_momentum_quality_60_20`:

| Metric | Value |
|---|---:|
| Raw IC | 0.0110 |
| Industry-neutral IC | 0.0090 |
| Residual IC | 0.0076 |
| Residual ICIR | 0.121 |
| Residual positive IC rate | 47.46% |
| Reference high redundancy | 0 |
| Style exposure high count | 0 |
| Residual research lead | false |

Blockers:

- industry-neutral mean IC below threshold;
- industry-neutral positive IC rate below threshold;
- residual mean IC below threshold;
- residual positive IC rate below threshold;
- residual yearly IC instability.

## Interpretation

This round produced a reusable factor source, a streaming residual prescreen path, and a corrected warmup policy. It produced no profitability evidence. The single-candidate Q2 smoke is weak but not redundant; reference and style exposure were not the blocker. The blocker was low residual IC and poor positive-rate shape.

## Next Required Action

Run the full 2015-2025 sharded residual prescreen across all six preregistered Round221 candidates before any portfolio grid, Sharpe ranking, return claim, or promotion discussion:

`round221_information_discreteness_full_long_cycle_sharded_residual_prescreen`
