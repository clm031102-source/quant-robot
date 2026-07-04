# CN Stock Round466 PS>10 Self-Risk Paper Ops Review

Date: 2026-07-04

Machine: office_desktop

Task: factor_batch

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Status: paper-ops package remains ready with the existing Round462 `ps_gt10` high-return lane; the Round465 self-risk overlay is blocked under the current strict OOS handoff gate.

## Progress Snapshot

Overall project progress is approximately 93%.

The project is cleaner after this step because the attractive Round465 overlay is no longer an ambiguous "maybe paper-ready" item. It has better full-sample and cost-stress drawdown, but it fails the same strict handoff gate used by the existing paper package.

The remaining gap to completion is still final validation quality: stronger OOS pass stability, fresh cost/capacity/tail review for any replacement lane, multiple-testing accounting, and the sealed final holdout read without retuning.

## Inputs

Review config:

- `configs/cn_stock_profit_sprint_ps_gt10_self_risk_paper_ops_review_20260704.json`

Local reports:

- Self-risk overlay: `data/reports/round465_ps_gt10_self_risk_overlay_20260704`
- OOS split audit: `data/reports/round465_ps_gt10_self_risk_oos_20260704`
- Cost-stress overlay: `data/reports/round465_ps_gt10_self_risk_cost_stress_20260704`
- Paper handoff review: `data/reports/round465_ps_gt10_self_risk_paper_handoff_review_20260704`
- Paper ops review: `data/reports/round465_ps_gt10_self_risk_paper_ops_review_20260704`

The review keeps the 2026 final holdout sealed and does not cross any broker, account, order, or live-trading boundary.

## OOS Split Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_shortlist_oos_split_audit.py --candidate ps_gt10_self_roll21_sum_m2_cash=data\reports\round465_ps_gt10_self_risk_overlay_20260704\ps_gt10_self_roll21_sum_m2_cash_events.csv:period_return --output-dir data\reports\round465_ps_gt10_self_risk_oos_20260704 --train-years 2,3,4,5 --test-years 1 --step-years 1 --date-column date --periods-per-year 50.4 --holding-period 20 --strict-min-annualized-return 0.03 --strict-min-overlap-sharpe 0.35 --strict-max-drawdown -0.30
```

Result:

- Candidate: `ps_gt10_self_roll21_sum_m2_cash`
- Split count: `30`
- Mean OOS annualized return: `0.1040420400`
- Mean OOS overlap Sharpe: `0.9060309956`
- Worst OOS drawdown: `-0.1245872164`
- Positive OOS rate: `0.9333333333`
- Strict pass rate: `0.6333333333`

Interpretation: the overlay has strong average OOS statistics and a much better drawdown profile, but the strict pass rate is below the current paper-handoff minimum of `0.75`.

## Cost Stress Overlay

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_shortlist_self_risk_overlay.py --return-source "ps_gt10_cost10=data\reports\round462_24h_profit_sprint_q20_ps_gt10_cost_stress_20260627\range_q20_ps_gt10_cost10_period_returns.csv|period_return" --return-source "ps_gt10_cost20=data\reports\round462_24h_profit_sprint_q20_ps_gt10_cost_stress_20260627\range_q20_ps_gt10_cost20_period_returns.csv|period_return" --return-source "ps_gt10_cost30=data\reports\round462_24h_profit_sprint_q20_ps_gt10_cost_stress_20260627\range_q20_ps_gt10_cost30_period_returns.csv|period_return" --policy roll21_sum_m2_cash --output-dir data\reports\round465_ps_gt10_self_risk_cost_stress_20260704 --return-column period_return --date-column date --periods-per-year 50.4 --holding-period 20
```

Results:

| Cost Stream | Annualized | Overlap Sharpe | Max DD |
| --- | ---: | ---: | ---: |
| cost10 + overlay | `0.0850798258` | `0.6969712817` | `-0.1245872164` |
| cost20 + overlay | `0.0802539889` | `0.6674444757` | `-0.1306887149` |
| cost30 + overlay | `0.0722381695` | `0.6027489688` | `-0.1367493818` |

Interpretation: the overlay is cost-stress friendly on full-sample returns. The failure is not cost drawdown; it is strict OOS split stability.

## Paper Handoff Review

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_simulation_shortlist_paper_handoff.py --config configs\cn_stock_profit_sprint_ps_gt10_self_risk_paper_ops_review_20260704.json --repo-root . --output-dir data\reports\round465_ps_gt10_self_risk_paper_handoff_review_20260704 --max-user-drawdown -0.30 --min-oos-strict-pass-rate 0.75
```

Summary:

- Candidate count: `3`
- Ready candidates: `2`
- Blocked candidates: `1`
- Default candidate: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`
- Primary high-return candidate: `paper_ready_cohort_entry_timed_range_q20_m175_ps_gt10_cash_cost10_vt08_max100_self_roll21_x08`

Candidate outcomes:

| Candidate | Status | Ann | Overlap Sharpe | Max DD | OOS strict pass | Blockers |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08` | ready | `0.0666337878` | `0.4961037387` | `-0.2621408725` | `0.9000000000` | none |
| `paper_ready_cohort_entry_timed_range_q20_m175_ps_gt10_cash_cost10_vt08_max100_self_roll21_x08` | ready | `0.0779414358` | `0.5654308054` | `-0.2542482237` | `0.7666666667` | none |
| `review_cohort_entry_timed_range_q20_m175_ps_gt10_self_roll21_m2_cash_cost10` | blocked | `0.0850798258` | `0.6969712817` | `-0.1245872164` | `0.6333333333` | `not_paper_ready`, `oos_strict_pass_rate_below_min` |

## Paper Ops Review

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_simulation_paper_ops_package.py --config configs\cn_stock_profit_sprint_ps_gt10_self_risk_paper_ops_review_20260704.json --paper-handoff data\reports\round465_ps_gt10_self_risk_paper_handoff_review_20260704\simulation_paper_handoff.json --output-dir data\reports\round465_ps_gt10_self_risk_paper_ops_review_20260704 --max-user-drawdown -0.30
```

Result:

- Status: `paper_ops_package_ready`
- Blockers: `0`
- Ready lanes: `2`
- Default lane: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`
- Primary high-return lane: `paper_ready_cohort_entry_timed_range_q20_m175_ps_gt10_cash_cost10_vt08_max100_self_roll21_x08`

Warnings:

- `capacity_not_clean_at_large_aum`
- `default_lane_kept_for_baseline_not_return_maximization`
- `final_holdout_sealed_promotion_blocked`
- `high_return_lane_is_diagnostic_role`
- `high_return_tail_contribution_concentrated`
- `shortlist_streams_highly_correlated`

## Decision

Do not replace the Round462 `ps_gt10` high-return paper lane with `ps_gt10_self_roll21_sum_m2_cash` under the current paper-handoff policy.

Keep the current paper package:

- Default baseline: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`
- High-return diagnostic lane: `paper_ready_cohort_entry_timed_range_q20_m175_ps_gt10_cash_cost10_vt08_max100_self_roll21_x08`

Carry the Round465 overlay only as blocked review evidence:

- It improves full-sample return, overlap Sharpe, max drawdown, and cost-stress drawdown.
- It fails the existing `0.75` strict OOS pass threshold.
- It should not be promoted, paper-started, or used as a reason to tune adjacent `q20`, `m175`, range-contraction, or `ps_ttm` thresholds.

Next useful work: rotate away from this same-family paper-lane repair and use either a genuinely orthogonal PIT source or a pre-registered paper-monitoring analysis that does not retune the existing q20/ps_gt10 lane.

## Safety Boundary

This remains research-to-paper only:

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
