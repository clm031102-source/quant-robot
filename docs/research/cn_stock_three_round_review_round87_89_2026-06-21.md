# CN Stock Three-Round Review Rounds 87-89 - 2026-06-21

## Scope

This review is the required 3-round governance checkpoint after Rounds 87, 88, and 89.

Machine/task/branch:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha
- Not scope: CN ETF rotation, live trading, broker/account/order actions

## Round Summary

| Round | Direction | Result | Useful Evidence | Decision |
|---:|---|---|---|---|
| 87 | Public QVM bottom-exclusion walk-forward | 2 frozen QVM leads both had 0/7 accepted folds | weak positive relative return, 0 capacity-limited trades | QVM hibernated |
| 88 | Tushare financial PIT readiness audit | current local Tushare roots had no financial statement or indicator dataset | 6,939 files scanned, 0 financial-like datasets, 0 PIT-ready datasets | profitability mining blocked until data layer exists |
| 89 | `fina_indicator` fixture ingestion smoke | new financial indicator path passed PIT readiness on fixture data | 4 rows, 2 assets, 2 quarters, 0 duplicate rows, 3/3 data files PIT-ready | data shape proven; live smoke required |

## Promotion Count

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research leads carried forward after Round89: data capability only, not factor candidates

## Bright Data

Round87 had weak but real loser-avoidance evidence:

| Factor | Accepted Folds | Mean Test Relative | Mean Test Overlap Sharpe | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---|
| `public_qvm_value_reversal_quality_20` | 0/7 | +1.07% | -0.0734 | 0 | rejected |
| `public_qvm_lowbeta_value_momentum_20` | 0/7 | +0.69% | -0.0807 | 0 | rejected |

Round89 produced the most useful engineering evidence:

- `fina_indicator` processed dataset can preserve both `ann_date` and `end_date`;
- PIT readiness can detect true profitability columns;
- manifest and quality-report files are excluded from financial dataset counts;
- fixture smoke has no missing numeric fields and no duplicate rows.

## Main Failure Pattern

The factor-mining failure pattern is now clear:

1. public price/volume and daily-basic proxy families found statistical ranking signals;
2. those signals repeatedly failed costed portfolio and walk-forward promotion gates;
3. daily-basic valuation/liquidity proxies are not true profitability data;
4. mining more proxy factors before real PIT financial data would repeat the same failure loop.

## Direction Adjustment

Stop:

- QVM direct TopN;
- QVM bottom-exclusion rescue;
- daily-basic proxy profitability claims;
- any profitability factor pre-registration before real `fina_indicator` smoke/backfill readiness.

Continue:

- real Tushare financial indicator ingestion;
- `ann_date` as information availability date;
- long-history quarterly backfill planning;
- PIT readiness before factor design;
- long-cycle, costed, capacity-aware walk-forward gates after factors exist.

## Next Rounds

Round90 should perform a real symbol-scoped Tushare `fina_indicator` smoke.

If Round90 passes, Round91 should move to:

`round91_tushare_fina_indicator_long_history_backfill_plan`

Budget stop-loss:

If real `fina_indicator` smoke or schema readiness fails, do not mine profitability factors. Record the data gap and either fix ingestion or rotate to another data-backed family with a real economic hypothesis.
