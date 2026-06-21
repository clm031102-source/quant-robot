# Round96 Profitability Quality Preregistration Design

## Objective

Pre-register profitability-quality factor candidates from clean PIT `fina_indicator` shard data and audit field/history coverage before any backtest.

This round turns the Round95 financial data capability into named, repeatable candidate definitions. It does not test Sharpe, profit, win rate, IC, or portfolio performance.

## Candidate Families

- Profitability level: ROE, ROA, net profit margin, gross margin.
- Growth quality: net profit growth, revenue growth, profit growth above revenue growth.
- Cash-profit quality: operating cash flow per share and year-over-year cash-flow improvement.
- Composite quality: profitability blend and growth-quality blend.
- Stability/change: four-quarter persistence and year-over-year improvement.

## Guardrails

- Use CN A-share stock scope only.
- Use Round95 shard 1 full100 PIT `fina_indicator` data.
- Use `ann_date` as information availability date.
- Reject any row where `ann_date < end_date`.
- Require duplicate financial keys = 0.
- Require missing asset id rows = 0.
- Require candidate field coverage before factor-matrix or IC work.
- Do not promote or paper-ready any candidate from preregistration alone.

## Acceptance Criteria

- A reusable `profitability_quality_preregistration` ops module exists.
- A CLI writes JSON, Markdown, and candidate coverage CSV.
- Unit tests cover passing coverage and blocking PIT/field failures.
- Real Round95 shard data produces a preregistration report.
- Startup gate advances to factor-matrix and label-alignment smoke only if coverage passes.

## Non-Goals

- No factor backtest.
- No IC or RankIC claim.
- No Sharpe/profit/win-rate claim.
- No full-universe financial backfill.
- No GitHub push.
- No broker, account, order, or live-trading action.
