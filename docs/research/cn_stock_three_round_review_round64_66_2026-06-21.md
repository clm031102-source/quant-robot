# CN Stock Three-Round Review Round64-66

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Scope

This review covers the daily-basic residual composite rotation after the `pv_corr` standalone line was hibernated.

- Round64: industry-neutral IC gate
- Round65: costed industry-neutral Top100 long-only conversion
- Round66: IC-to-portfolio gap and bottom-exclusion overlay diagnostic

## Evidence

Round64 found strong industry-neutral IC in three pre-registered daily-basic residual factors. The best neutral Rank IC values were 0.0556, 0.0546, and 0.0425.

Round65 rejected all six long-only portfolio cases. Best total return was 30.84%, best overlap-adjusted Sharpe was 0.1733, best relative return was -2342.91%, and all rejections came from `relative_return_below_threshold`. Capacity was not the blocker.

Round66 found five IC-to-portfolio translation gaps and zero promotable long-only cases. Bottom-exclusion diagnostics produced two stable risk-filter leads across both rebalance intervals:

- `resid_value_low_turnover_quality_20`
- `resid_value_reversal_low_tail_20`

`resid_value_quality_low_vol_20` failed the overlay test and is removed from the next batch.

## Reject Reason Histogram

- `relative_return_below_threshold`: 6 portfolio cases
- `translation_gap`: 5 IC-to-portfolio cases
- `weak_or_unproven_signal`: 1 IC-to-portfolio case
- `weak_or_unproven_exclusion`: 1 factor across both overlay runs

## Direction Adjustment

Do not expand raw Top100 long-only parameters for this family. The economic shape is not "buy the best names"; it is "avoid the bottom tail." The next batch must test only the two bottom-exclusion candidates in a costed portfolio.

Public-method mapping:

- Alphalens-style lesson: keep IC and quantile/return translation separate.
- Qlib-style lesson: use pre-registered datasets and reusable configs rather than ad hoc notebooks.
- vectorbt/pyfolio-style lesson: portfolio metrics, costs, drawdown, and fold stability decide usefulness, not IC alone.
- WorldQuant-style lesson: compact formula families are acceptable only when they survive independent translation and robustness gates.

## Budget Stop-Loss

Stop extending this daily-basic residual family if the next costed bottom-exclusion portfolio fails both conditions:

- overlap-adjusted Sharpe at or above 0.5, and
- drawdown within the configured absolute risk limit.

If it fails, rotate away from daily-basic residual overlays to a new public-method family rather than adding more windows or TopN settings.

## Next Step

Run Round67:

`daily_basic_residual_costed_bottom_exclusion_portfolio_batch`

Use `configs/experiment_grid_cn_stock_daily_basic_residual_exclusion_candidates_round67_20260621.json` and report both rebalance intervals under realistic cost, impact, capacity, fold, and drawdown gates.
