# CN Stock Round453 Analyst Report Revision Preregistration

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

## Reason For Rotation

Round450-452 closed the `entry_limit_down` execution-risk line as simulation observation only. The next factor-mining action must use a genuinely different point-in-time source, not more tradeability-string, valuation-threshold, or public-technical parameter tuning.

Round453 selects Tushare `report_rc` analyst reports as an external expectation-revision source. This is economically different from the recent Dragon-Tiger, Alpha101/public-technical, range-contraction, PB/PS, and entry tradeability families.

## Hypothesis

Sell-side target price, EPS, net-profit forecast, and rating revisions may proxy changing market expectations. If the information is not fully incorporated immediately, a PIT-safe signal could predict future cross-sectional returns after controlling for coverage, size, liquidity, industry, and style exposure.

## Registered Candidates

- `analyst_target_upside_60`
- `analyst_np_revision_90`
- `analyst_eps_revision_90`
- `analyst_revision_target_composite_90`

These are source-screen candidates only. No portfolio grid or promotion is allowed before source smoke, PIT alignment, full non-holdout sample replay, neutral IC, OOS/walk-forward, costs, capacity, regime, and multiple-testing checks.

## First Action

Run the candidate-plan gate, then run a small-window source smoke for 2024-01-01 through 2025-12-31. Do not start the full 2015-2025 cache unless:

- the endpoint is available;
- rows and assets are non-trivial;
- row-cap warnings are manageable with smaller windows;
- report dates can be shifted to later tradable signal dates;
- no 2026 final-holdout data is used for tuning.

## Stop Conditions

Stop or rotate if the source is unavailable, nearly empty, too sparse for neutral IC, or too slow for the 24h sprint. Do not continue this family past three rounds without a written audit.
