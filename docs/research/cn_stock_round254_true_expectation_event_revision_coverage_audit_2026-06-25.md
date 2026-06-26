# CN Stock Round254 True Expectation Event Revision Coverage Audit

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round251-253 produced zero usable factors. Round254 was therefore set to:

`round254_rotate_to_true_expectation_event_revision_or_coverage_audit`

This audit checks whether the project already has enough true expectation or event-revision data, such as forecast or earnings express surprise, to justify another factor-mining pass. The audit used local reports and caches only; no new Tushare live pull was required.

## Local Evidence Reviewed

- Round146 event preregistration:
  `docs/research/cn_stock_event_factor_preregistration_round146_2026-06-22.md`
- Round147 event PIT/IC prescreen:
  `docs/research/cn_stock_event_factor_pit_ic_prescreen_round147_2026-06-22.md`
- Round147 result packet:
  `data/reports/event_factor_pit_ic_prescreen_round147_20260622/event_factor_pit_ic_prescreen.json`
- Current Round254 startup gate:
  `data/reports/round254_startup_method_protocol_20260625/factor_mining_startup_gate.json`

## Coverage Findings

Round146 proved that true event data is not entirely missing:

| Endpoint / query | Evidence |
|---|---|
| `forecast` endpoint smoke | available |
| `forecast_ann_date` cross-section probe | 2,210 rows, cross-section ready |
| `express` endpoint smoke | 0 rows, blocked in sample |
| `express_start_end` cross-section probe | 1,377 rows, cross-section ready |

Round147 then pulled broader PIT event data:

| Endpoint | Rows |
|---|---:|
| `forecast` | 6,916 |
| `dividend` | 15,996 |
| `repurchase` | 9,575 |
| `stk_holdernumber` | 164,422 |
| `top10_holders` | 192,000 |
| `top10_floatholders` | 180,000 |

So forecast/express is not an unknown idea. Forecast was already tested in a live PIT event prescreen, but the resulting factor did not work.

## Forecast Result Audit

`event_forecast_profit_revision_1q` failed before portfolio testing:

| Horizon | IC obs | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Lead |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 11 | -0.0415 | -0.221 | -0.73 | 36.4% | -0.0082 | 0.3253 | -0.0468 | no |
| 5 | 11 | 0.0033 | 0.022 | 0.07 | 54.5% | 0.0045 | 0.2604 | -0.0065 | no |

Blockers:

- Not FDR-significant.
- Mean IC below threshold.
- ICIR below threshold.
- Size-neutral IC below gate.
- 20-day direction and quantile spread negative.
- Only 11 IC observations despite 6,916 forecast rows, so the usable cross-sectional signal dates were low-power.

## Adjacent Event Evidence

The event system itself can find a real research lead. Round147 found one:

`event_dividend_cash_yield_announced_1y`, 20-day horizon:

- IC 0.1082
- ICIR 0.629
- t-stat 6.62
- IC positive rate 75.7%
- Q5-Q1 0.0223
- Industry-neutral IC 0.2780
- Size-neutral IC 0.1003
- Research lead: yes
- Promotion: no

But Round148 later needed de-duplication and event-specific audits before portfolio conversion. This means the event framework is useful, but forecast alone is not currently a direct alpha path.

## Decision

Round254 should not directly rerun the old forecast formula or the old 130-symbol statement-surprise formula grid.

Allowed next work:

- Build or audit a cached, sharded forecast/express event dataset before mining a new expectation-revision factor.
- If using forecast again, the new hypothesis must be orthogonal to `event_forecast_profit_revision_1q`, for example:
  - forecast surprise confirmed by cash quality,
  - forecast revision interacted with analyst-style dispersion proxy,
  - forecast surprise filtered by announcement timing and industry reporting season,
  - forecast/express disagreement or confirmation.
- Require a coverage target before IC: more than 30 signal dates and broad multi-year coverage, not the 11-observation Round147 state.
- Keep 2026 final holdout blocked.

## Next Direction

`round255_rotate_to_forecast_express_event_cache_or_orthogonal_preregistration_after_coverage_audit`

If a broad forecast/express cache cannot be built quickly, rotate away from true expectation events rather than spending more budget on another low-power financial-event formula.
