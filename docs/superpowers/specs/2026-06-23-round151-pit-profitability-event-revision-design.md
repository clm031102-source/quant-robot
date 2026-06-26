# Round151 PIT Profitability Event Revision Design

## Context

Round149 preregistered six lottery/MAX-effect candidates. Round150 replayed them across 2015-2025 and rejected the family as a standalone long alpha: positive IC existed in several rows, but quantile spread and portfolio translation failed. The startup gate now requires the next direction:

`round151_rotate_to_pit_profitability_event_revision_preregistration`

Earlier Round96-99 profitability-quality work also failed as static `fina_indicator` level/growth factors. Round151 must not repeat those static quality definitions. It should focus on information timing: announced revisions, surprises, and confirmation events.

## Design

Create a new preregistration module for PIT-aware profitability event revision candidates:

`src/quant_robot/ops/profitability_event_revision_preregistration.py`

The module will define candidate specs with:

- `factor_name`
- `family`
- `formula_template`
- `direction`
- required financial columns and optional Tushare event endpoints
- event date fields
- PIT controls
- public reference tags
- expected failure modes
- portfolio/promotion permissions fixed to false

The module will load existing `fina_indicator` PIT inputs with the already-tested loader from `profitability_quality_preregistration`. It will run a coverage gate by candidate, using `ann_date` as information availability and rejecting candidates that need missing columns or too few eligible assets/rows. Optional endpoint availability probes can be injected for forecast/express candidates; missing endpoint evidence should block only those endpoint-dependent candidates, not the whole round if enough financial-only revision candidates pass.

Candidate families:

- `fina_revision_event`: announced quarter-over-quarter or year-over-year changes from PIT `fina_indicator`.
- `cash_quality_surprise`: cash-flow confirmation of profit growth.
- `margin_revision`: margin and profitability improvement at announcement dates.
- `forecast_revision_event`: forecast/express event hypotheses gated by endpoint availability.
- `revision_confirmation_blend`: candidates that require future prescreen to combine forecast/express surprise with historical quality confirmation.

## Candidate Budget

Round151 will pre-register 10 candidates, with at least 6 coverage-passed candidates required from local PIT financial data and at least 3 families. No candidate can enter a portfolio grid directly.

Expected candidates:

- `pit_fina_netprofit_yoy_revision_1q`
- `pit_fina_revenue_profit_revision_spread_1q`
- `pit_fina_margin_revision_yoy_4q`
- `pit_fina_roe_revision_persistence_4q`
- `pit_fina_cash_profit_revision_4q`
- `pit_fina_cash_earnings_confirmation_1q`
- `pit_fina_quality_surprise_blend_1q`
- `pit_forecast_profit_revision_event_1q`
- `pit_express_profit_surprise_event_1q`
- `pit_forecast_express_quality_confirmation_1q`

## Gates

Round151 is preregistration only.

Hard blockers:

- missing PIT dates;
- `ann_date < end_date`;
- duplicate financial keys;
- duplicate candidate names;
- endpoint-dependent candidates marked available without endpoint proof;
- any candidate with `portfolio_backtest_allowed` or `promotion_allowed`;
- same names as the rejected Round96 static profitability-quality candidates.

Next required gate after successful preregistration:

`round152_pit_profitability_event_revision_matrix_and_label_smoke`

Round152 must build factor values, align them strictly after `ann_date`, and check label coverage before any IC screen.

## Non-Goals

This round will not:

- calculate Sharpe, profit rate, win rate, portfolio return, or drawdown;
- tune formulas after looking at returns;
- use 2026 final holdout;
- claim profitability or paper readiness;
- revive Round96 static quality factors under new names.

## Verification

Required verification:

- unit tests for coverage, duplicate blocking, endpoint blocking, and static-family name rejection;
- CLI test writing JSON, Markdown, and CSV;
- candidate plan gate clears discovery and keeps portfolio/promotion blocked;
- startup gate still clears with Round151 source audit and direction;
- data/report paths remain untracked by Git.
