# CN Stock Tushare Daily-Basic Alpha Factory Pre-Registration Round83 - 2026-06-21

## Purpose

Round82 rejected the frozen anti-SuperTrend bottom-exclusion walk-forward and hibernated the SuperTrend family.

Round83 rotates away from public technical indicators and uses the existing Tushare daily-basic alpha factory as a controlled replay. This is not a new broad manual factor search. It is a multiple-testing-aware check of the currently available Tushare daily-basic factor set.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Prior Evidence To Respect

Repeated blockers through Round82:

- IC can be strong while long-only portfolios fail.
- Bottom-tail exclusion is often real but still does not pass costed walk-forward.
- Public technical indicators have repeatedly failed after long-cycle replay, costs, capacity, and walk-forward validation.
- Parameter expansion after zero accepted folds is budget waste.

Therefore Round83 must not:

- reopen SuperTrend, RSRS, OBV, RSI/Bollinger, or price-volume formula parameter sweeps;
- promote IC-only rows;
- use uncorrected p-values after multiple factor tests;
- tune after reading final holdout data;
- treat daily-basic proxy fields as true profitability-quality data unless the required fields exist.

## Hypothesis

The currently available Tushare daily-basic fields may contain weak but explainable value, dividend, liquidity, turnover, and market-cap information. The alpha factory should determine whether any pre-registered daily-basic factor survives:

- sufficient samples;
- cost and market-impact assumptions;
- capacity controls;
- multiple-testing correction;
- directionality checks;
- paper-candidate rejection reasons.

If none survive, the result should become a data/method decision:

- stop mining weak daily-basic proxy variants;
- add or audit Tushare financial-indicator/profitability-quality data before claiming to mine profitability factors.

## Required Evaluation Order

1. Confirm current startup gate and CN stock data manifest.
2. Run the existing Tushare daily-basic alpha factory on the available processed CN stock data.
3. Require adjusted IC significance after Bonferroni correction.
4. Review cost, impact, capacity, trade count, IC observations, and long-short observations.
5. Write a Round83 audit report with:
   - hypothesis count;
   - adjusted-significant count;
   - paper-eligible count;
   - top rejected rows and rejection reasons;
   - explicit data-field coverage limits.

Promotion remains blocked unless the candidate also enters later costed long-cycle and walk-forward validation.

## Candidate Source

Use the existing implementation:

- `scripts/run_tushare_alpha_factory.py`
- `src/quant_robot/research/alpha_factory.py`
- factor source: `tushare_daily_basic`

The factory uses registered Tushare daily-basic factor names from:

- `src/quant_robot/factors/tushare_inputs.py`

## Stop-Loss Rule

Hibernate daily-basic alpha-factory proxy mining if:

- adjusted-significant candidates = 0;
- paper-eligible candidates = 0;
- or all apparent winners are blocked by capacity, insufficient samples, or weak directionality.

If that happens, the next useful work is not more proxy factor names. The next useful work is Tushare financial-indicator/profitability-quality data readiness.
