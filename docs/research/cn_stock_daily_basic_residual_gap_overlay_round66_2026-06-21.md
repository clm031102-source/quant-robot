# CN Stock Daily-Basic Residual Gap And Overlay Round66

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Diagnose why the Round64 daily-basic residual IC signals failed the Round65 costed industry-neutral Top100 long-only portfolio test, then test whether the surviving signals are more useful as bottom-quantile exclusion overlays.

## Inputs

- Portfolio leaderboard: `data/reports/industry_neutral_portfolio_daily_basic_residual_composite_round65_20260621/leaderboard.csv`
- Grid config: `configs/experiment_grid_cn_stock_daily_basic_residual_composite_round64_20260621.json`
- Bottom quantile: 20%
- Rebalance intervals: 5 and 10
- Period: 2015-01-05 through 2025-12-31
- Forward horizon: 20
- Execution lag: 1

## IC-To-Portfolio Gap Audit

Output: `data/reports/ic_portfolio_gap_audit_daily_basic_residual_composite_round66_20260621`

- Cases: 6
- Strong RankIC cases: 5
- IC-to-portfolio gap cases: 5
- Promotable long-only cases: 0
- Capacity-limited cases: 0
- Translation status:
  - `translation_gap`: 5
  - `weak_or_unproven_signal`: 1
- Decision reason:
  - `relative_return_below_threshold`: 6

Interpretation: the family contains statistical ranking signal, but the current Top100 long-only construction does not translate it into enough absolute or relative return.

## Bottom-Exclusion Overlay Results

Output:

- `data/reports/bottom_exclusion_overlay_daily_basic_residual_composite_round66_20260621_reb5`
- `data/reports/bottom_exclusion_overlay_daily_basic_residual_composite_round66_20260621_reb10`

| Factor | Rebalance | Classification | Dates | Mean Full | Mean Kept | Mean Bottom | Overlay Excess | Overlay t | Positive Rate | Kept Compounded | Full Compounded |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `resid_value_low_turnover_quality_20` | 5 | bottom_exclusion_candidate | 530 | 0.0046 | 0.0054 | 0.0014 | 0.0008 | 4.14 | 59.32% | 137.68% | 55.85% |
| `resid_value_reversal_low_tail_20` | 5 | bottom_exclusion_candidate | 530 | 0.0051 | 0.0058 | 0.0024 | 0.0007 | 3.09 | 59.17% | 189.74% | 102.39% |
| `resid_value_quality_low_vol_20` | 5 | weak_or_unproven_exclusion | 530 | 0.0049 | 0.0048 | 0.0051 | -0.0001 | -0.24 | 50.00% | 109.14% | 114.15% |
| `resid_value_low_turnover_quality_20` | 10 | bottom_exclusion_candidate | 265 | 0.0053 | 0.0061 | 0.0020 | 0.0008 | 3.09 | 57.79% | 76.28% | 42.17% |
| `resid_value_reversal_low_tail_20` | 10 | bottom_exclusion_candidate | 265 | 0.0057 | 0.0065 | 0.0025 | 0.0008 | 2.67 | 59.85% | 95.74% | 58.85% |
| `resid_value_quality_low_vol_20` | 10 | weak_or_unproven_exclusion | 265 | 0.0056 | 0.0055 | 0.0057 | -0.0000 | -0.13 | 48.67% | 62.63% | 64.65% |

## Interpretation

Two factors survive as risk-filter leads:

- `resid_value_low_turnover_quality_20`
- `resid_value_reversal_low_tail_20`

They are not standalone buy signals. Their useful shape is bottom-tail avoidance: excluding the weakest 20% improves kept-basket return in both rebalance schedules. `resid_value_quality_low_vol_20` does not pass the overlay test and should be dropped from the next costed portfolio batch.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- Costed long-only factor: 0
- Bottom-exclusion diagnostic leads: 2
- Dropped from next batch: `resid_value_quality_low_vol_20`
- Next config: `configs/experiment_grid_cn_stock_daily_basic_residual_exclusion_candidates_round67_20260621.json`
- Next step: costed bottom-exclusion portfolio validation with 10 bps cost, 20 bps impact, 1% ADV cap, and absolute drawdown gate
