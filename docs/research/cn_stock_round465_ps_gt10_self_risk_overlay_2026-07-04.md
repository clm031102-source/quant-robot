# CN Stock Round465 PS>10 Self-Risk Overlay

Date: 2026-07-04

Machine: office_desktop

Task: factor_batch

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Status: paper-lane risk repair improved; no independent alpha or final promotion claim.

## Progress Snapshot

Overall project progress is approximately 92%.

Round464 closed the residual moneyflow route as a benchmark-relative rejection. Round465 moved to the more efficient current gap: hardening the existing Round462 `ps_gt10` high-return paper lane with fixed, prior-information-only self-risk overlays.

The remaining gap to project completion is still final evidence, not repository hygiene: any candidate that moves beyond paper observation still needs cost and capacity replay, tail contribution review, strict out-of-sample robustness, multiple-testing accounting, and a sealed final holdout read without retuning.

## Startup Gates

- `scripts/start_task_context.py --machine office_desktop --task factor_batch`
- `scripts/run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-execution-aware-round465-20260704`
- `scripts/run_factor_mining_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-execution-aware-round465-20260704 --commits-allowed --pushes-allowed --confirm-start`
- `scripts/run_cn_stock_data_manifest.py --data-root data/processed/office_desktop_20260616_combined_research --output-dir data/reports/round465_execution_aware_startup_manifest_20260704`
- `scripts/run_factor_mining_candidate_plan_gate.py --candidate-plan configs/factor_mining_candidate_plan_round465_ps_gt10_self_risk_overlay_20260704.json --output-dir data/reports/round465_ps_gt10_self_risk_candidate_plan_gate_20260704`

Gate status:

- Quant PM startup gate: ready, no blockers.
- Factor-mining startup gate: cleared, no blockers.
- Candidate plan gate: research ready, no blockers, 9 / 9 control areas complete.
- CN stock data manifest: review required, no blockers.

Data manifest warnings:

- Extreme return rows are present.
- Moneyflow symbol coverage is below bar coverage.

## Pre-Registered Candidate

Candidate plan:

- `configs/factor_mining_candidate_plan_round465_ps_gt10_self_risk_overlay_20260704.json`

Candidate:

- `ps_gt10_self_roll21_sum_m2_cash`

Family:

- `paper_lane_execution_aware_self_risk_overlay`

Source stream:

- `data/reports/round462_24h_profit_sprint_q20_tail_attribute_cash_filter_20260627/cash_ps_gt_10_official_template_period_returns.csv`

Policy boundary:

- Use only the existing Round462 `ps_gt10` paper-lane return stream.
- Do not tune `q20`, `m175`, range-contraction parameters, or `ps_ttm` thresholds.
- Do not claim a new independent alpha.
- Keep promotion disabled.

## Self-Risk Overlay Result

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_shortlist_self_risk_overlay.py --return-source ps_gt10=data\reports\round462_24h_profit_sprint_q20_tail_attribute_cash_filter_20260627\cash_ps_gt_10_official_template_period_returns.csv --output-dir data\reports\round465_ps_gt10_self_risk_overlay_20260704 --return-column period_return --date-column date --periods-per-year 50.4 --holding-period 20
```

Local output:

- `data/reports/round465_ps_gt10_self_risk_overlay_20260704/shortlist_self_risk_overlay.json`
- `data/reports/round465_ps_gt10_self_risk_overlay_20260704/shortlist_self_risk_overlay_summary.csv`

Top fixed overlay:

- Candidate: `ps_gt10_self_roll21_sum_m2_cash`
- Policy: `roll21_sum_m2_cash`
- Annualized return: 0.08507982577628304
- Overlap-adjusted Sharpe: 0.6969712816692145
- Max drawdown: -0.12458721638476855
- Average self-risk exposure: 0.7049723756906078
- Guard event share: 0.2950276243093923

Baseline:

- Candidate: `ps_gt10`
- Annualized return: 0.07794143577038515
- Overlap-adjusted Sharpe: 0.565430805392886
- Max drawdown: -0.2542482236517434
- Average self-risk exposure: 1.0
- Guard event share: 0.0

Interpretation:

The fixed `roll21_sum_m2_cash` guard improved the already packaged Round462 `ps_gt10` paper lane on return, overlap-adjusted Sharpe, and max drawdown. The strongest improvement is drawdown: -25.42% to -12.46%.

## Overlay Walk-Forward Result

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_turnover_low_overlay_walk_forward.py --period-returns data\reports\round462_24h_profit_sprint_q20_tail_attribute_cash_filter_20260627\cash_ps_gt_10_official_template_period_returns.csv --output-dir data\reports\round465_ps_gt10_overlay_walk_forward_20260704 --return-column period_return --decision-date-column date --periods-per-year 50.4 --holding-period 20 --train-years 3 --test-years 1 --step-years 1
```

Local output:

- `data/reports/round465_ps_gt10_overlay_walk_forward_20260704/turnover_low_overlay_walk_forward.json`
- `data/reports/round465_ps_gt10_overlay_walk_forward_20260704/turnover_low_overlay_walk_forward_policy_summary.csv`

Best fixed policy:

- Policy: `entry_cash_dd_warn10_cut20`
- Folds: 7
- Average test annualized return: 0.08511501025984347
- Average test overlap-adjusted Sharpe: 0.792769836233477
- Worst test drawdown: -0.15096641704796288
- Positive test rate: 0.7142857142857143
- Strict pass rate: 0.7142857142857143

Train-selected policy summary:

- Folds: 7
- Selected average test annualized return: 0.08002216634358725
- Selected average test overlap-adjusted Sharpe: 0.7706125510047508
- Selected worst test drawdown: -0.19380408078297084
- Selected strict pass rate: 0.7142857142857143
- Selected policies: `entry_cash_dd_warn10_cut20` 3 folds, `entry_cash_no_overlay` 3 folds, `entry_cash_vol_target_8` 1 fold.

Interpretation:

The calendar walk-forward overlay check supports the risk-repair direction, but it does not by itself promote a new candidate. The fixed drawdown overlay improved worst OOS drawdown versus the baseline/no-overlay policy while keeping the same positive-test and strict-pass rates.

## Decision

Keep `ps_gt10_self_roll21_sum_m2_cash` as a stronger paper-simulation risk-repair candidate.

Do not promote it as an independent alpha.

Do not treat this as permission to tune `q20`, `m175`, range-contraction, or `ps_ttm` thresholds.

The next useful work is to rebuild the paper handoff or paper-ops package with this fixed overlay as a candidate lane, then rerun cost, capacity, tail-contribution, and simulation replay checks.

## Safety Boundary

This remains research-to-paper only:

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
