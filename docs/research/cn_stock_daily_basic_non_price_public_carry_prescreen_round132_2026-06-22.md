# CN Stock Daily-Basic Non-Price Public Carry Prescreen Round132

Date: 2026-06-22

## Scope

Round132 executed the preregistered Round131 daily-basic non-price public carry candidates on CN stocks. The run used daily-basic fields only for signal construction. Price bars were used only for forward-return labels and capacity diagnostics.

This is an Alphalens-style coverage, IC, quantile, turnover, and capacity prescreen. It is not a portfolio backtest and creates no paper-ready or live signal.

## Data Window

- Bars: 2015-01-05 to 2025-12-31, 10,785,537 rows, 5,707 assets.
- Daily-basic inputs: 2023-07-03 to 2025-12-31, 3,262,000 rows, 5,567 assets.
- Final holdout: 2026 excluded.
- Factor rows: 32,620,000.
- Label rows: 21,417,227.
- Aligned rows: 63,526,270 across 10 factors and 2 horizons.

## Gate Results

- Candidates tested: 10.
- Factor x horizon tests: 20.
- FDR-significant tests: 20.
- Coverage-pass candidates after row-level field and capacity checks: 3.
- Research leads: 1.
- Promotion allowed: 0.

The coverage gate was tightened during implementation. A candidate now needs row-level field coverage >=80% on at least 80% of rows, plus capacity-clean rows >=80%. This prevented high-IC but partially sparse daily-basic signals from being incorrectly treated as clean leads.

## Research Lead

`daily_basic_free_float_supply_quality_20`, horizon 20:

- Mean Spearman IC: 0.0392.
- ICIR: 0.3113.
- t-stat: 7.54.
- IC positive rate: 63.5%.
- Q5-Q1 spread: 0.5015.
- Quantile monotonicity: 0.900.
- Top-quantile turnover: 0.91%.
- Median cross-section: 5,349.
- Field coverage clean ratio: 99.39%.
- Capacity clean ratio: 96.45%.

Interpretation: this is a slow daily-basic share-structure plus value signal. It is the only candidate that passed statistics, field coverage, capacity, positive top-minus-bottom spread, and quantile monotonicity together.

## Notable Non-Leads

`daily_basic_valuation_reversion_quality_60` had the strongest raw IC:

- Horizon 20 mean IC 0.0701, ICIR 0.5276, t-stat 12.77.
- Q5-Q1 spread 0.2090 and monotonicity 0.700.
- Blocker: field coverage clean ratio only 68.86%, below the 80% gate.

This is useful evidence, but not a clean lead. It should not enter portfolio conversion until the missing daily-basic field coverage is explained or repaired without post-hoc tuning.

`daily_basic_value_yield_size_neutral_20` passed coverage, but failed quantile monotonicity:

- Horizon 20 mean IC 0.0509, ICIR 0.3406.
- Q5-Q1 spread 0.0535.
- Quantile monotonicity 0.500, below lead threshold.

`daily_basic_crowding_value_yield_balance_20` passed coverage, but the spread direction was negative at both horizons. It should not be inverted or promoted without a new preregistration.

## Decision

Round132 produced one research lead and zero promotable factors.

Next direction: `round133_daily_basic_non_price_carry_dedup_before_portfolio_conversion`.

Round133 should test whether `daily_basic_free_float_supply_quality_20` is redundant with existing size/value/liquidity factors and whether the 20-day lead survives a narrow portfolio-conversion preflight. No broad parameter sweep, no inversion of failed candidates, and no direct promotion from IC.

Generated report directory:

`data/reports/daily_basic_non_price_public_carry_prescreen_round132_20260622`
