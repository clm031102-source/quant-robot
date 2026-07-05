# CN Stock Round555 Startup Gate Alignment And Daily-Basic Smoke

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: repair the CN stock factor-mining startup packet so downstream strict validators accept it, preregister a daily-basic source-readiness smoke, and run a short local processed-bars alpha-factory screen without provider calls or final-holdout tuning.

## Startup Gate Alignment

Problem reproduced:

```text
CN stock factor mining startup gate round state decision is unsupported
```

The default CN stock startup gate wrote `status=cleared`, but the same packet failed `validate_cleared_startup_gate_packet` because `round_state.last_three_round_decision` contained free-form prose instead of a supported enum.

Fix:

- Changed `configs/factor_mining_startup_cn_stock.json` to use `last_three_round_decision=rotate_family`.
- Aligned `round_state.next_direction` with the repeatable protocol direction.
- Kept the strict validator, but allowed `family_rotation_required=true` to be satisfied by the explicit `rotate_family` decision enum rather than requiring the word `rotate` inside `next_direction`.
- Added a regression assertion that the default config packet is immediately accepted by `validate_cleared_startup_gate_packet`.

Current round-state packet:

| Field | Value |
| --- | --- |
| Last completed round | 462 |
| Next round | 463 |
| Decision | `rotate_family` |
| Next direction | `paper_simulation_packaging_or_new_pit_source_not_q20_threshold_tuning` |
| Family rotation required | true |

## Gates

Startup and project gates:

- `scripts/start_task_context.py --machine office_desktop --task factor_batch`: branch matched.
- `scripts/run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-round555-20260705`: ready.
- `scripts/run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-round555-20260705 --commits-allowed --pushes-allowed --confirm-start`: cleared.

Data manifest for the local combined root:

| Field | Value |
| --- | ---: |
| Source root | `data\processed\office_desktop_20260616_combined_research` |
| Bar rows | 3,806,375 |
| Bar symbols | 5,634 |
| Moneyflow rows | 3,606,228 |
| Moneyflow symbols | 5,312 |
| Date range | 2023-07-03 to 2026-06-15 |

Manifest status was `review_required` with known warnings:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

Candidate plan:

- Config: `configs/factor_mining_candidate_plan_round555_daily_basic_source_smoke_20260705.json`
- Gate status: `research_ready`
- Candidates: 12 active daily-basic factors.
- Complete control areas: 9 / 9.
- Research screen allowed: true.
- Portfolio grid allowed: false.
- Promotion allowed: false.

## Alpha-Factory Smoke

Command class:

```powershell
python scripts\run_tushare_alpha_factory.py --source processed-bars --data-root data\processed\office_desktop_20260616_combined_research --market CN --factor-source tushare_daily_basic --factor-input-root data\processed\office_desktop_20260617_daily_basic_factor_inputs\processed\factor_inputs --output-dir data\reports\round555_tushare_daily_basic_alpha_factory_smoke_20260705 --start-date 2024-01-02 --end-date 2024-01-31 --top-n 5 --cost-bps 10 --execution-lag 1 --allow-review-required-data-manifest
```

Result summary:

| Metric | Value |
| --- | ---: |
| Hypotheses | 12 |
| Completed | 12 |
| Failed | 0 |
| Adjusted-significant IC screens | 6 |
| Alpha-factory internal paper-eligible rows | 3 |

Top rows:

| Rank | Factor | Adj p | ICIR | Sharpe | Total return | Capacity-limited trades | Internal eligible |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `ps_ttm_inverse` | 0.008241 | 0.7788 | -3.3225 | -0.0800 | 0 | true |
| 2 | `dv_ttm` | 0.001082 | 0.8983 | -3.5900 | -0.0792 | 0 | true |
| 3 | `volume_ratio` | 0.039515 | 0.6742 | -8.3860 | -0.3195 | 0 | true |
| 4 | `circ_mv_log` | 0.219950 | 0.5412 | 1.0061 | 0.0133 | 0 | false |
| 5 | `total_mv_log` | 0.341744 | 0.5026 | -0.6901 | -0.0095 | 0 | false |
| 6 | `turnover_rate_low` | 0.441393 | 0.4791 | -3.2834 | -0.0707 | 24 | false |
| 7 | `pb_inverse` | 0.005928 | 0.7993 | -5.2885 | -0.1480 | 4 | false |
| 8 | `pe_ttm_inverse` | 0.000281 | 0.9703 | -5.5509 | -0.1021 | 11 | false |
| 9 | `volume_ratio_low` | 0.039515 | -0.6742 | -6.1822 | -0.2034 | 22 | false |
| 10 | `turnover_rate` | 0.441393 | -0.4791 | -7.9119 | -0.3183 | 0 | false |
| 11 | `turnover_rate_f` | 0.300641 | -0.5140 | -11.3729 | -0.4777 | 0 | false |
| 12 | `turnover_rate_f_low` | 0.300641 | 0.5140 | -11.9249 | -0.1792 | 42 | false |

Interpretation:

- The local daily-basic source and experiment plumbing now run through the required startup/data/candidate-plan gates.
- This is a short January 2024 smoke, not a discovery claim, not a long-cycle replay, and not a promotion package.
- The strongest IC rows still show poor short-window portfolio returns, and several value/low-turnover variants trigger capacity flags.
- The `paper_candidate_allowed` field is only the alpha-factory internal screen; project promotion remains false because the candidate plan blocks portfolio and promotion stages.

## Verification

- Red test first failed on unsupported round-state decision.
- After enum alignment, the same test exposed next-direction drift.
- Final focused test passed: `tests.unit.test_factor_mining_startup_gate_cli.FactorMiningStartupGateCliTests.test_default_cn_stock_config_is_runnable`.
- Startup gate suites passed: 44 tests.
- Python compile passed for `src\quant_robot\ops\factor_mining_startup.py` and `scripts\run_factor_mining_startup_gate.py`.

## Decision

Round555 repaired a real gate inconsistency and produced local source-readiness evidence. No result is promoted. The next useful work is to extend the gated smoke into a longer 2024 discovery-window diagnostic or add an explicit alpha-factory candidate-plan packet check before execution so script runs cannot drift away from preregistered candidates.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download was used for the alpha-factory smoke.
- No 2026 final-holdout tuning was performed.
- Generated `data/reports` artifacts remain out of Git.
