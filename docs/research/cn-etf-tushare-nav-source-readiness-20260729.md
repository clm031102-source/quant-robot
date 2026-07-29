# CN ETF Tushare NAV Source Readiness — 2026-07-29

## Decision

Status: `ready_for_nav_premium_preregistration`.

The Tushare `fund_nav` source passed every frozen point-in-time, completeness,
cross-source agreement, breadth, and safety gate. This decision authorizes only
a separate hash-bound preregistration for one delayed-NAV premium-innovation
candidate. It is not factor-performance evidence and does not authorize a
factor batch, portfolio grid, walk-forward run, paper signal, broker
connection, account read, order placement, or live trading.

## Quantitative Evidence

- Target requests: 1,069 terminal; 1,067 completed, 2 deterministic empty, 0 failed.
- Canonical source: 705,081 rows, 1,067 ETFs, 1,087 official analysis sessions.
- Frozen NAV window: 2020-01-02 through 2024-06-28; no out-of-window or 2026 rows.
- Duplicate `asset_id`/`nav_date` rows: 0.
- Valid `ann_date >= nav_date`: 705,055 rows, 99.996312%.
- Finite positive `unit_nav`: 705,081 rows, 100%.
- Strict `known_from` violations after calendar-tail repair: 0.
- Public comparison keys: 642,285; matched: 642,284, or 99.999844%.
- Public comparison assets: 1,020; matched: 1,020, or 100%.
- Agreement within 10 bp: 642,283 of 642,284 matched rows, or 99.999844%.
- Severe disagreement above 5%: 1 row, or 0.000156%.
- Sessions with at least 30 usable assets: 1,087 of 1,087, or 100%.

One source repair was evidence-driven and did not alter a threshold. ETF
`516690.SH` NAV dated 2024-06-06 was announced on 2024-07-30. Extending the
official-calendar tail from 2024-07-05 to 2024-08-02 established the correct
2024-07-31 `known_from`; the retained NAV window and sealed final holdout did
not change.

The local no-network rerun reproduced the source-readiness JSON SHA-256
exactly.

## Source Identity

- Config SHA-256: `0cc8f1d5ea88e1c262b32d3b698275e0552df1da7f65df5a3cbc9c50de032814`
- Readiness result SHA-256: `151a30944fd4ca62fd765af2a48fa33b5dc3997e469af7bf923b126179b53f8b`
- Request manifest SHA-256: `35a2c5331b2ca3efae870010c2604099be4ab6d6ec6b1046208d3038a1f2e920`
- Canonical NAV SHA-256: `8cbc3a63561dbfcb0a42dcef56b053da484c149f32f1554ff271c1875cb6338a`
- Session coverage SHA-256: `9b1483919cafeaf497ecea2581eeb7193408f2995c9f5edc22bd02fe48704f1e`
- NAV agreement SHA-256: `62d4b65694a1fa5d3d204e9fa76702d71b2946ee92956a5aa80562102f64a7c4`

Generated source data and reports remain outside Git.

## Small-Capital Economics

The current operator envelope is CNY 1,000–3,000, 0.5 bp commission per side,
10 bp slippage per side, a CNY 5 minimum-commission stress, 252 sessions
maximum holding period, CNY 1,000 maximum single position, CNY 60 daily-loss
cap, and 1% ADV maximum one-way participation.

- Base proportional round trip: 21 bp.
- CNY 5 minimum-fee stress at CNY 3,000 notional: 53.33 bp round trip.
- CNY 5 minimum-fee stress at CNY 1,000 notional: 120 bp round trip.
- User absolute drawdown veto: 40%.
- Stricter paper-promotion drawdown cap: 8%.

The base historical prescreen must therefore report at least 10.5 bp per side,
and the minimum-fee stress must be evaluated separately before any paper
promotion. Small capital does not remove the need for cost, capacity, or
lot-size checks.

## Remaining Physical Gates

Even a passing historical candidate cannot complete the existing paper gate
inside one day. Promotion still requires at least 20 elapsed paper-observation
days, 30 fills, two market regimes, and drawdown no worse than 8%. Broker
integration remains a disabled schema/checklist boundary until those elapsed
observations exist.
