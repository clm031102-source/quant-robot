# CN Stock Daily-Basic Residual Composite Round64

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Start the post-`pv_corr` rotation with a small, public-method-backed daily-basic residual composite family. The first gate is industry-neutral IC only; no portfolio promotion claim is allowed from this round.

## Inputs

- Config: `configs/experiment_grid_cn_stock_daily_basic_residual_composite_round64_20260621.json`
- Factor source: `daily_basic_residual_composite`
- Factors: 3
- Period: 2015-01-05 through 2025-12-31
- Forward horizon: 20
- Execution lag: 1
- Daily-basic input root: `configs/cn_stock_authority_daily_basic_inputs_2015_2025.json`
- Stock industry metadata: `data/processed/cn_stock_metadata`

## Industry-Neutral IC Results

Output: `data/reports/industry_neutral_ic_audit_daily_basic_residual_composite_round64_20260621`

- Input rows: 24,952,335
- Date-factor rows: 7,938
- Industry-neutral signal factors: 3 / 3
- Industry-exposure dominated factors: 0 / 3
- Weak or unproven factors: 0 / 3
- Missing industry rows: 303,575

| Factor | Overall Rank IC | Overall t | Neutral Rank IC | Neutral t | Retention |
|---|---:|---:|---:|---:|---:|
| `resid_value_low_turnover_quality_20` | 0.0355 | 14.49 | 0.0556 | 39.51 | 1.57 |
| `resid_value_reversal_low_tail_20` | 0.0327 | 12.95 | 0.0546 | 35.39 | 1.67 |
| `resid_value_quality_low_vol_20` | 0.0150 | 5.20 | 0.0425 | 26.40 | 2.83 |

## Interpretation

This family clears the first public-method gate better than the retired `pv_corr` standalone line:

- factors are economically interpretable;
- industry-neutral IC survives strongly;
- the source uses purchased Tushare daily-basic data;
- the candidate set is small and pre-registered.

The metadata gap still blocks promotion-grade review, but it does not block the next portfolio-conversion test.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- IC research leads: 3
- Next step: industry-neutral top-N portfolio conversion with cost, capacity, drawdown, fold, and relative-return gates
