# CN Stock PIT Profitability Event Revision Controlled IC Neutral Prescreen Round153

## Scope

- Machine/task: office_desktop / factor_validation.
- Market/asset: CN stock cross-sectional alpha, not ETF rotation.
- Input candidates: 7 active Round151 PIT profitability event/revision factors; 3 endpoint-dependent candidates stayed frozen.
- Data window: bars 2015-01-05 to 2025-12-31; signal dates 2015-04-16 to 2025-11-11.
- Gate type: full-sample controlled IC prescreen with FDR, industry neutral IC, size neutral IC, liquidity neutral IC, and Round96 static profitability-quality reference de-duplication.
- This round does not compute Sharpe, total return, annual return, win rate, drawdown, or portfolio evidence.

## Key Numbers

| Metric | Value |
|---|---:|
| Active candidates | 7 |
| Frozen endpoint candidates | 3 |
| Factor rows | 28,010 |
| Label rows | 509,966 |
| Aligned rows | 56,020 |
| Factor x horizon tests | 14 |
| FDR-significant tests | 0 |
| Industry/size/liquidity neutral-gate pass tests | 0 |
| Research leads | 0 |
| Promotion allowed candidates | 0 |

## Best Raw Results

| Factor | Horizon | Mean IC | ICIR | t-stat | IC>0 | Q5-Q1 | Industry neutral IC | Size neutral IC | Liquidity neutral IC | Round96 ref max abs corr | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| pit_fina_margin_revision_yoy_4q | 20 | 0.0459 | 0.265 | 1.43 | 58.6% | 0.0193 | 0.1442 | 0.0406 | 0.0341 | 1.000 | no |
| pit_fina_revenue_profit_revision_spread_1q | 5 | 0.0428 | 0.275 | 1.51 | 46.7% | 0.0039 | 0.1903 | 0.0314 | 0.0317 | 0.674 | no |
| pit_fina_netprofit_yoy_revision_1q | 5 | 0.0283 | 0.201 | 1.10 | 50.0% | 0.0055 | 0.1824 | 0.0150 | 0.0173 | 0.682 | no |

## Failure Diagnosis

- No result survived FDR. The best raw IC rows had weak t-stats around 1.43 to 1.51 and ICIR below 0.30.
- Industry-neutral IC was often positive, but size-neutral and liquidity-neutral t-stats did not clear the gate. This suggests part of the apparent signal is tied to broad style/liquidity structure rather than a robust stock-specific profitability event edge.
- `pit_fina_margin_revision_yoy_4q` is too close to the rejected Round96 static reference `fina_net_margin_improvement_yoy` with max absolute correlation 1.000.
- `pit_fina_cash_earnings_confirmation_1q` is too close to Round96 static cash/profitability references, with max absolute correlations up to 0.993.
- The family is not promotable and should not enter a portfolio grid without a new preregistered repair hypothesis or new endpoint data.

## Decision

- Research leads: 0.
- Paper-ready candidates: 0.
- Manual/live candidates: 0.
- Next direction: `round154_rotate_or_repair_profitability_event_revision_after_neutral_prescreen_failure`.
- The PIT profitability event/revision family should be hibernated unless the next round brings new data availability, a new event-timing thesis, or a preregistered formula repair that explicitly addresses size/liquidity exposure and Round96 duplication.

