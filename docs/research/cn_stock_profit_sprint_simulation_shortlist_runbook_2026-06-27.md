# CN Stock Profit Sprint Simulation Shortlist Runbook

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

This runbook packages the current 24h sprint candidates for the next simulation/backtest stage.

Machine role:

`office_desktop`

Task:

`factor_validation`

Config:

`configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`

2026 final holdout remains sealed.

## Candidate Tiers

| Tier | Candidate ID | Use |
|---|---|---|
| High-return default | `primary_high_return` | Main candidate if return is prioritized and around 30% drawdown is acceptable |
| Preferred defensive | `primary_defensive_zz500` | Main candidate if drawdown/cost robustness matters more |
| Ultra-defensive reference | `safer_defensive_zz500` | Benchmark for low-drawdown simulation; not the main return candidate |

## Parameters

### `primary_high_return`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost_rate_0.001 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

Core parameters:

- replacement filter: drop bottom 10% `turnover_rate_f` candidates and replace from the remaining candidate list;
- volatility target: target annual vol 6%, lookback 84 event returns;
- no external regime overlay.

Key evidence:

- total return: +177.08%;
- annualized return: +6.35%;
- Sharpe: 0.960;
- overlap Sharpe: 0.517;
- max drawdown: -28.88%;
- mean OOS annualized return: +7.86%;
- worst OOS drawdown: -24.00%;
- 30 bps fixed-exposure cost stress total: +130.29%;
- CSI500 beta R2: 0.251.

### `primary_defensive_zz500`

Formula:

`primary_high_return + zz500_mom120_neg_half`

External regime:

- benchmark: `CN_ETF_XSHG_510500`;
- signal: 120-day ETF momentum;
- risk-off rule: if momentum is negative before decision date, multiply exposure by 0.5.

Key evidence:

- total return: +147.29%;
- annualized return: +5.62%;
- Sharpe: 1.001;
- overlap Sharpe: 0.536;
- max drawdown: -20.38%;
- mean OOS annualized return: +6.05%;
- worst OOS drawdown: -14.87%;
- 30 bps fixed-exposure cost stress total: +114.75%;
- 30 bps strict pass: 90.00%;
- CSI500 beta-hedged annualized return: +5.59%.

### `safer_defensive_zz500`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost_rate_0.001 + cash_low_turnover_f_bottom20 + entry_cash + vol_target_5_lb84 + zz500_mom120_neg_half`

Core parameters:

- cash bottom 20% `turnover_rate_f` entry trades instead of replacing them;
- volatility target: target annual vol 5%, lookback 84 event returns;
- same CSI500 120-day momentum half-exposure regime overlay.

Key evidence:

- total return: +114.76%;
- annualized return: +4.73%;
- Sharpe: 0.996;
- overlap Sharpe: 0.534;
- max drawdown: -14.94%;
- mean OOS annualized return: +4.72%;
- worst OOS drawdown: -11.68%;
- CSI500 beta-hedged annualized return: +4.69%.

## Do Not Use

These outputs are superseded and must not be used as evidence:

- `data/reports/round346_24h_profit_sprint_cost_stress_primary_aggressive_20260627`
  - reason: volatility-target exposure recomputation did not reproduce official current-cost events.
- `data/reports/round347_24h_profit_sprint_benchmark_beta_audit_20260627`
  - reason: OLS residual stream subtracted the intercept; corrected audit uses `strategy_return - beta * benchmark_return`.

Rejected defaults:

- aggressive low20/PB candidate;
- hard cash external regime as default;
- strategy self-risk cash overlays;
- direct public-indicator cash filters from Round336.

## Before 2026 Holdout

Do not run the 2026 holdout until all are true:

1. The simulation shortlist config has been reviewed.
2. Candidate formulas are implemented or mapped in a repeatable entrypoint.
3. Cost, capacity, and beta audits are linked in the report.
4. The user explicitly starts final validation or simulation-readiness review.
5. The run is recorded as read-once holdout usage.

## Current Recommendation

Use two candidates in the next simulation stage:

- `primary_high_return` for return-seeking simulation;
- `primary_defensive_zz500` for the more realistic default if drawdown and cost robustness matter.

Keep `safer_defensive_zz500` as a low-drawdown reference, not as the primary return engine.
