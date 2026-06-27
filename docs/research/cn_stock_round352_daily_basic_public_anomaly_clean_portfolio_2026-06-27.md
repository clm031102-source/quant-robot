# CN Stock Round352 - Daily-Basic Public Anomaly Clean Portfolio Diagnostic

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round352 deliberately rotated away from the current low-turnover champion family and away from already-rejected public technical/event families.

The tested family used locally available daily-basic and bar data:

- value;
- dividend yield/carry;
- quality/low-volatility proxies;
- reversal;
- liquidity/capacity filters;
- public anomaly residual ensembles.

Output:

`data/reports/round352_24h_profit_sprint_daily_basic_public_anomaly_clean_portfolio_20260627`

2026 final holdout remains unused.

## Run

Entrypoint:

`scripts/run_daily_basic_clean_portfolio_diagnostic.py`

Key settings:

- window: 2015-01-01 through 2025-12-31;
- candidates: 12;
- cases: 48;
- TopN: 50 and 100;
- holding period: 20;
- rebalance interval: 5;
- execution lag: 1;
- costs: 10 and 30 bps;
- min signal-date amount: 10,000,000;
- excluded asset prefix: `CN_XBEI`;
- max absolute daily return quarantine: 50%;
- portfolio value: 1,000,000;
- max participation rate: 5%.

Summary:

| Metric | Value |
|---|---:|
| Candidate factors | 12 |
| Cases | 48 |
| Factor rows | 14,842,457 |
| Diagnostic pass cases | 0 |
| Best case | `daily_basic_dividend_value_stability_carry_20_top50_hold20_reb5_cost10_cap1e+06` |

## Top Rows

| Factor | TopN | Cost | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Worst Year | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `daily_basic_dividend_value_stability_carry_20` | 50 | 10 bps | +84.26% | +4.04% | 0.437 | 0.231 | -47.37% | -23.46% | fail |
| `daily_basic_value_yield_size_neutral_20` | 50 | 10 bps | +85.68% | +3.96% | 0.427 | 0.229 | -51.19% | -29.02% | fail |
| `daily_basic_value_yield_size_neutral_20` | 100 | 10 bps | +72.91% | +2.56% | 0.320 | 0.172 | -55.97% | -29.44% | fail |
| `daily_basic_midcap_value_yield_capacity_20` | 50 | 10 bps | +57.69% | +2.87% | 0.320 | 0.164 | -53.12% | -29.83% | fail |
| `daily_basic_volume_ratio_crowding_reversal_20` | 50 | 10 bps | +47.99% | +2.41% | 0.282 | 0.148 | -52.30% | -30.23% | fail |

Main blockers:

- overlap-adjusted Sharpe below threshold;
- max drawdown below the user tolerance floor used by this diagnostic;
- extreme-trade excluded results degrade sharply.

The best row has no capacity issue at 1,000,000 portfolio value, but capacity alone is not enough when overlap Sharpe and drawdown fail.

## Interpretation

This family does not compete with the current short list:

| Candidate | Ann. | Overlap Sharpe | Max DD |
|---|---:|---:|---:|
| Current high-return `primary_high_return` | +6.35% | 0.517 | -28.88% |
| Current balanced `primary_balanced_zz500_75` | +5.99% | 0.530 | -24.74% |
| Current defensive `primary_defensive_zz500` | +5.62% | 0.536 | -20.38% |
| Best Round352 daily-basic public anomaly | +4.04% | 0.231 | -47.37% |

The result is useful negative evidence. It says not to blindly rotate into plain value/yield/public-anomaly TopN portfolios just because the current best factor family started from daily-basic data.

## Decision

Do not add any Round352 factor to the simulation shortlist.

Hibernate this exact direction:

`daily_basic_public_anomaly_clean_portfolio_direct_topn_after_round352_zero_pass`

Allowed future use:

- use value/yield/liquidity as secondary filters or tie-breakers inside the existing robust low-turnover/replacement framework;
- do not promote direct TopN value/yield public-anomaly portfolios without a new orthogonal thesis and better drawdown controls.

Next work:

- audit Round350-352 as a three-round block;
- next family should focus on improving the existing candidate's risk-adjusted construction or finding a new PIT event/source with enough coverage, not re-running failed public-indicator or plain value grids.
