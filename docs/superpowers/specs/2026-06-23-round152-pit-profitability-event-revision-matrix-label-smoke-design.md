# Round152 PIT Profitability Event Revision Matrix Label Smoke Design

## Context

Round151 pre-registered 10 PIT profitability event/revision candidates from local `fina_indicator` data. Seven financial-only candidates are active. Three forecast/express candidates are frozen until endpoint coverage proof exists.

Round152 must not calculate IC, Sharpe, profit rate, win rate, portfolio return, or drawdown. Its job is narrower: prove that active candidate factor values can be computed and joined to forward-return labels without look-ahead.

## Design

Create a dedicated Round152 module:

`src/quant_robot/ops/profitability_event_revision_matrix_label_smoke.py`

The module will:

- load PIT `fina_indicator` inputs from the existing financial loader;
- load CN daily bars from one or more processed bars roots;
- read the Round151 preregistration JSON;
- optionally read the candidate-plan gate JSON to determine active versus frozen candidates;
- compute only the seven active financial-only revision candidates;
- attach a signal date as the first tradable bar strictly after `ann_date`;
- build forward-return labels with `execution_lag >= 1`;
- verify `signal_date > ann_date`, `entry_date > signal_date`, and `exit_date > entry_date`;
- report label coverage and per-candidate coverage;
- keep portfolio, promotion, and paper claims disabled.

## Active Candidate Formulas

- `pit_fina_netprofit_yoy_revision_1q`: `netprofit_yoy - lag(netprofit_yoy, 1)`
- `pit_fina_revenue_profit_revision_spread_1q`: `(netprofit_yoy - or_yoy) - lag(netprofit_yoy - or_yoy, 1)`
- `pit_fina_margin_revision_yoy_4q`: `netprofit_margin - lag(netprofit_margin, 4)`
- `pit_fina_roe_revision_persistence_4q`: `(roe - lag(roe, 4)) + 0.5 * rolling_mean(roe, 4)`
- `pit_fina_cash_profit_revision_4q`: `(ocfps - lag(ocfps, 4)) - 0.25 * abs(netprofit_yoy - or_yoy)`
- `pit_fina_cash_earnings_confirmation_1q`: `z(netprofit_yoy) + z(ocfps / abs(cfps))`
- `pit_fina_quality_surprise_blend_1q`: `0.3*z(delta_roe_1q) + 0.3*z(delta_margin_1q) + 0.2*z(delta_ocfps_1q) + 0.2*z(netprofit_yoy - or_yoy)`

Z-scores are cross-sectional by report period for smoke-stage normalization only.

## Gates

Round152 passes only if:

- at least one active candidate exists;
- all active candidates have implemented formulas;
- bars and labels are available;
- label coverage meets the configured threshold;
- alignment violations are zero;
- frozen endpoint candidates remain inactive;
- portfolio and promotion policies remain false.

## Outputs

The writer will emit:

- `profitability_event_revision_matrix_label_smoke.json`
- `profitability_event_revision_matrix_label_smoke.md`
- `profitability_event_revision_matrix_candidate_summary.csv`

## Next Step

If Round152 passes, the next allowed step is a controlled IC/neutral prescreen. It still must use multiple-testing accounting and cannot jump directly to a portfolio grid.
