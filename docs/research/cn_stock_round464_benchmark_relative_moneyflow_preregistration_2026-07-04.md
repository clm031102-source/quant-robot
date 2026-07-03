# CN Stock Round464 Benchmark-Relative Moneyflow Pre-Registration

Date: 2026-07-04

Machine: office_desktop

Task: factor_batch

Branch: `codex/factor-batch-cn-stock-benchmark-relative-20260704`

Status: complete rejection set; no profitability or promotion claim.

## Progress Snapshot

Overall project progress is approximately 91%.

The repository is now cleaner than it was at the start of this task: current cloud `main` was used as the base, a dated task branch was created, the factor-mining startup gates were rerun, the Round464 candidate was pre-registered, and the corrected benchmark-relative walk-forward completed.

The remaining gap to a completed project is still research evidence, not plumbing: a factor needs to pass point-in-time source screening, long-cycle walk-forward, cost and capacity checks, regime coverage, multiple-testing controls, and a sealed final holdout read. Round464 did not clear that bar.

## Startup Gates

- `scripts/start_task_context.py --machine office_desktop --task factor_batch`
- `scripts/run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-benchmark-relative-20260704`
- `scripts/run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-benchmark-relative-20260704 --commits-allowed --pushes-allowed --confirm-start`
- `scripts/run_cn_stock_data_manifest.py --data-root data/processed/office_desktop_20260616_combined_research --output-dir data/reports/round464_benchmark_relative_startup_manifest_20260704`

Gate status:

- Quant PM startup gate: ready, no blockers.
- Factor-mining startup gate: cleared, no blockers.
- CN stock data manifest: review required, no blockers.

Data manifest warnings:

- Extreme return rows are present.
- Moneyflow symbol coverage is below bar coverage.

## Pre-Registered Candidate

Candidate plan:

- `configs/factor_mining_candidate_plan_round464_benchmark_relative_moneyflow_20260704.json`

Walk-forward config:

- `configs/walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704.json`

Candidate:

- `large_resid_liq_vol_amt_gate_20`

Family:

- `benchmark_relative_moneyflow_residual_validation`

Policy:

- This was a frozen validation preflight for an already implemented residual moneyflow factor.
- No formula tuning, portfolio grid expansion, or 2026 final-holdout tuning was allowed.
- Promotion was explicitly disabled in the candidate plan.

## Framework Fixes Found During Round464

The Round464 run exposed three framework issues that are now fixed and covered by unit tests:

1. Walk-forward config loading dropped several `ExperimentGridConfig` fields.
   - Preserved now: `asset_universe_path`, `min_signal_amount`, `max_calendar_holding_days`, `write_case_artifacts`, `resume_completed_cases`, and `reuse_research_inputs`.

2. Test-fold warmup only considered factor windows.
   - It now also considers regime lookbacks and signal average amount windows, so regime-filtered folds receive enough pre-split history.

3. Long experiment grids could not reuse completed train/test sub-runs.
   - `run_experiment_grid()` now reloads a completed output directory when `resume_completed_cases` is true and the cached case set matches the current config.

## Walk-Forward Result

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704.json --source processed-bars --data-root data\processed\office_desktop_20260616_combined_research --allow-no-accepted
```

Local output:

- `data/reports/walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704/manifest.json`
- `data/reports/walk_forward_tushare_moneyflow_benchmark_relative_round464_20260704/walk_forward_leaderboard.csv`

Summary:

- Cases: 6
- Folds: 4
- Accepted: 0
- Rejected: 6

Best ranked case:

- `CN_large_resid_liq_vol_amt_gate_20_top6_cost20_reb1_regime252`
- Validation status: rejected
- Accepted folds: 1 / 4
- Mean test relative return: -0.4880795133304834
- Mean test Sharpe: 2.345181173077507
- Worst test max drawdown: -0.26447967717564735
- Capacity-limited trades: 0
- Tail IC p-value: 0.9119684672528218
- Rejection reasons: train not completed, relative return below threshold, insufficient accepted folds, adjusted IC significance not passed.

Least rejected cost-20 regime case by accepted folds:

- `CN_large_resid_liq_vol_amt_gate_20_top6_cost20_reb1_regime150`
- Validation status: rejected
- Accepted folds: 2 / 4
- Mean test relative return: -0.48946110669454157
- Mean test Sharpe: 2.204918284089979
- Worst test max drawdown: -0.26447967717564735
- Capacity-limited trades: 0
- Tail IC p-value: 0.9776750340912199
- Rejection reasons: relative return below threshold, adjusted IC significance not passed.

Cost-30 stress also rejected:

- Mean test relative return range: -0.849490373080496 to -0.8562921555945933
- Worst test max drawdown reached -0.3215341170496724.

## Decision

Round464 is complete evidence against promoting this residual moneyflow candidate in the benchmark-relative validation frame.

Do not promote `large_resid_liq_vol_amt_gate_20`.

Do not continue this candidate by tuning top-N, cost, or regime thresholds.

The next useful research move is a family rotation toward new orthogonal information or a position-sizing/risk-construction idea that is pre-registered before any portfolio backtest.

## Safety Boundary

This remains research-to-paper only:

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
