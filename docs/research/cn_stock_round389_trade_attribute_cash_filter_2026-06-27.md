# CN Stock Round389 - Trade Attribute Cash Filter

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round389 tested whether simple structural selected-trade attributes can improve the frozen official low-turnover template.

The tested filters were pre-defined and not selected by full-sample loss ranking:

- missing `stock_market`;
- non-mainboard;
- STAR Market;
- ChiNext;
- missing industry;
- missing exchange;
- northbound eligible;
- not northbound eligible.

Each filter cashes flagged selected trades by subtracting their `entry_cash_proxy_weighted_return` contribution from the frozen official template.

## New Tooling

- `src/quant_robot/ops/shortlist_trade_attribute_cash_filter.py`
- `scripts/run_shortlist_trade_attribute_cash_filter.py`
- `tests/unit/test_shortlist_trade_attribute_cash_filter.py`

This generic tool can project any selected-trade attribute filter onto an official template using specs such as:

`name=column:operator:value`

Supported operators include `eq`, `ne`, `in`, `not_in`, `missing`, and `not_missing`.

## Output

`data/reports/round389_24h_profit_sprint_trade_attribute_cash_filter_projection_20260627`

## Result

Official template base:

- total return: +150.65%;
- annualized return: 5.71%;
- overlap Sharpe: 0.428;
- max drawdown: -35.29%.

| Candidate | Flagged Trades | Matched Contribution | Ann. | Overlap | Max DD | Decision |
|---|---:|---:|---:|---:|---:|---|
| `cash_star_market` | 1,283 | 0.0000 | 5.71% | 0.428 | -35.29% | no effect |
| `cash_chinext` | 639 | 0.0000 | 5.71% | 0.428 | -35.29% | no effect |
| `cash_missing_stock_market` | 3,545 | +0.0158 | 5.62% | 0.428 | -34.62% | reject; lower return |
| `cash_non_mainboard` | 5,467 | +0.0158 | 5.62% | 0.428 | -34.62% | reject; lower return |
| `cash_missing_industry` | 3,556 | +0.0158 | 5.62% | 0.428 | -34.62% | reject; lower return |
| `cash_missing_exchange` | 3,545 | +0.0158 | 5.62% | 0.428 | -34.62% | reject; lower return |
| `cash_not_northbound_eligible` | 3,453 | +0.1159 | 5.05% | 0.445 | -30.76% | reject; large return loss |
| `cash_northbound_eligible` | 19,452 | +0.8340 | 0.79% | 0.277 | -10.58% | reject; removes the return engine |

The non-mainboard result is mostly a missing-metadata effect, not a board effect: STAR and ChiNext selected trades carried zero matched contribution in this template.

## Decision

Do not add any trade-attribute cash filter to the simulation shortlist.

The useful process output is the generic attribute projection tool. The research output is negative:

- board filters do not improve the current template;
- missing metadata filters reduce return;
- northbound eligibility filters mostly separate where the current return stream lives, but do not improve return-risk enough to be useful.

## Process Lesson

Industry/board metadata is still valuable for audits, but blunt board or metadata exclusions are not the right improvement path. A future industry constraint should test concentration and risk-budgeting, not cashing whole structural buckets.
