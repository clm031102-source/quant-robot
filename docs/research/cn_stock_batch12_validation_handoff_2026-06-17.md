# CN Stock Batch 12 Validation Handoff - 2026-06-17

## Purpose

This handoff freezes the Batch 12 discovery result before any 2025 validation read. It is a pre-registration artifact, not validation evidence.

## Scope

- Machine role: office/high-spec desktop factor validation
- Required task type: `factor_validation`
- Required branch pattern: `codex/factor-validation-cn-stock-...`
- Market: `CN`
- Asset type: `stock`
- Discovery source: `data/reports/cn_stock_champion_staggered_schedule_20260617`
- Discovery window used: `2023-07-03` through `2024-12-31`
- Validation window allowed next: `2025-01-01` through `2025-12-31`
- Final holdout: `2026-01-01` through `2026-06-15`, not allowed for the next step

## Frozen Candidates

Validate only these two candidates unless the user explicitly authorizes a new discovery task:

| Candidate | Cost bps | Schedule | Hold | Top N | Discovery return | Discovery Sharpe | Discovery max DD | Discovery RankIC | Discovery Tail RankIC |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost10_prev_month_ret_gt_neg1` | 10 | every1 offset0 | 20 | 50 | 0.1967 | 6.5375 | -0.0416 | 0.0755 | 0.1339 |
| `rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost20_prev_month_ret_gt_neg1` | 20 | every1 offset0 | 20 | 50 | 0.1753 | 5.8811 | -0.0431 | 0.0755 | 0.1339 |

## Required Controls

- Use the 2025 validation window only.
- Carry forward the 137 related discovery hypotheses when interpreting significance.
- Report cost, capacity, turnover, max participation, drawdown, RankIC, Tail RankIC, monthly stability, and accepted/rejected status.
- Compute overlap-aware return statistics because hold20 with daily refresh creates non-independent daily observations.
- Report `naive_sharpe`, `autocorr_adjusted_sharpe`, `newey_west_standard_error_mean`, `newey_west_t_stat_mean`, `variance_inflation`, `effective_sample_size`, `autocorrelations`, and `overlap_risk_flag`.
- Compare every1 candidates against every2/every3 schedule controls as diagnostics, not as newly optimized replacements.
- Treat discovery Sharpe above 5 as a red flag, not evidence of promotability.
- Do not tune factor components, thresholds, schedule interval, offset, top N, hold period, or cost after reading 2025 results.
- Do not read 2026 final holdout during this validation pass.

## Promotion Rule

Promotion remains blocked unless a candidate survives 2025 validation after costs, capacity, turnover, drawdown, RankIC/Tail RankIC, monthly stability, and overlap-aware checks. Passing discovery plus failing OOS means the candidate is rejected or returned to a new discovery task; it is not adjusted inside the validation task.
