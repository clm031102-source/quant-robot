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
| Balanced observation | `primary_balanced_zz500_75` | Return/risk middle lane; useful if the user accepts mid-20% drawdown for higher return |
| Preferred defensive | `primary_defensive_zz500` | Main candidate if drawdown/cost robustness matters more |
| Ultra-defensive reference | `safer_defensive_zz500` | Benchmark for low-drawdown simulation; not the main return candidate |
| Quality-filter defensive observation | `primary_ps_filtered_defensive_zz500` | Defensive comparison that cashes selected high-PS entries instead of replacing them |

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

### `primary_balanced_zz500_75`

Formula:

`primary_high_return + zz500_mom120_neg_mult_0.75`

External regime:

- benchmark: `CN_ETF_XSHG_510500`;
- signal: 120-day ETF momentum;
- risk-off rule: if momentum is negative before decision date, multiply exposure by 0.75.

Key evidence:

- total return: +161.99%;
- annualized return: +5.99%;
- Sharpe: 0.989;
- overlap Sharpe: 0.530;
- max drawdown: -24.74%;
- mean OOS annualized return: +6.95%;
- worst OOS drawdown: -19.55%;
- 30 bps fixed-exposure cost stress total: +122.57%;
- 30 bps strict pass: 76.67%;
- CSI500 beta-hedged annualized return: +5.96%.

Interpretation:

This is a simulation observation lane, not a replacement for `primary_defensive_zz500`. It is materially stronger on return than the 50% defensive version, but weaker on 30 bps cost strict-pass robustness.

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

### `primary_ps_filtered_defensive_zz500`

Formula:

`primary_high_return + cash selected entries with top 20% selected-basket ps_ttm + zz500_mom120_neg_half`

Secondary filter:

- start from the selected `primary_low10_vol6` basket;
- rank selected entries by `ps_ttm` on each signal date;
- cash entries in the highest 20% selected-basket PS rank;
- do not replace filtered entries.

External regime:

- same CSI500 120-day momentum half-exposure overlay as `primary_defensive_zz500`.

Key evidence:

- total return: +119.29%;
- annualized return: +4.86%;
- Sharpe: 1.076;
- overlap Sharpe: 0.573;
- max drawdown: -15.90%;
- mean OOS annualized return: +5.01%;
- worst OOS drawdown: -12.02%;
- 30 bps fixed-exposure cost stress total: +96.15%;
- 30 bps strict pass: 76.67%;
- CSI500 beta-hedged annualized return: +4.83%;
- CSI500 beta-hedged overlap Sharpe: 0.943.

Interpretation:

This is a defensive observation lane. It is not the return engine, but it is useful for comparing whether a valuation-quality cash filter can reduce tail risk while keeping positive return.

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

## Mandatory Replay Gates

Before packaging any shortlist candidate for simulation, run both replay gates:

```powershell
.venv\Scripts\python.exe scripts\run_simulation_shortlist_replay.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round363_24h_profit_sprint_simulation_shortlist_event_schema_replay_20260627 --metric-tolerance 0.005
```

The replay must show:

- `status` is `passed`;
- `blocked_candidate_count` is 0;
- every candidate has a valid return column;
- structured candidates have `decision_date`;
- volatility-target or regime-overlay candidates have `final_exposure`;
- declared ZZ500 risk-off multipliers match the event stream when the event file declares a multiplier.

Round363 passed these checks for all five candidates.

## Exposure / Pre-Rank Gates

Round366-368 added two required controls for any candidate that changes untradeable positions, board eligibility, or replacement behavior:

```powershell
.venv\Scripts\python.exe scripts\run_shortlist_exposure_audit.py --trades <trades_with_tradeability.parquet> --output-dir <exposure_audit_output> --group-column industry --group-column stock_market
```

```powershell
.venv\Scripts\python.exe scripts\run_turnover_low_prerank_replacement.py --output-dir <prerank_replacement_output> --exclude-asset-prefix CN_XBEI --max-abs-daily-return-quarantine 0.50
```

The evidence must distinguish:

- true alpha improvement;
- reduced wasted weight from board-permission or ST/delisting blocks;
- accidental risk reduction from cashing untradeable positions;
- added crash exposure from replacing previously cashed positions.

Round368 rejected `replace_drop_turnover_f_low10_mainboard_prerank` for simulation shortlist use:

- entry allowed rate improved to 95.75%;
- annualized return improved to 6.86%;
- max drawdown worsened to -48.95%;
- even `vol_target_4_lb84` still had -36.71% max drawdown.

So board-permission pre-ranking is now a process control, not a promoted alpha line.

## Before 2026 Holdout

Do not run the 2026 holdout until all are true:

1. The simulation shortlist config has been reviewed.
2. Candidate formulas are implemented or mapped in a repeatable entrypoint.
3. Cost, capacity, and beta audits are linked in the report.
4. The user explicitly starts final validation or simulation-readiness review.
5. The run is recorded as read-once holdout usage.

## Block Dependence Check

Round356 added a reusable block-dependence audit:

`scripts/run_shortlist_return_block_audit.py`

Result:

- all five shortlist candidates stayed positive after removing the most important year;
- the most sensitive removed year is 2015 for every candidate;
- top three months contributed about 43.75% to 48.26% of total log return, below the 70% blocker threshold;
- 2026 final holdout remains sealed.

This does not make the candidates paper-ready. It does reduce the concern that the current shortlist is only one lucky year or one lucky month cluster.

Round357 stress-tested stricter block gates:

- 0 of 5 candidates passed when requiring at least +3% leave-one-year annualized return, at least 0.40 leave-one-year overlap Sharpe, and no more than 45% top-three-month log contribution;
- this is a warning against overselling the family as smooth all-regime alpha;
- the useful ranking is: balanced 75% and defensive 50% are the best core simulation candidates, high-return is a drawdown-tolerant lane, PS-filter is a defensive diagnostic lane, safer defensive is only an ultra-defensive reference.

Round361 added a replay check:

`scripts/run_simulation_shortlist_replay.py`

It verifies that the event-return files reproduce the metrics stored in the config. This caught and fixed the `safer_defensive_zz500` source-column issue: the final CSI500-regime stream is `overlay_return`, not `period_return`.

## Current Recommendation

Use three active candidates in the next simulation stage:

- `primary_high_return` for return-seeking simulation;
- `primary_balanced_zz500_75` for return/risk middle simulation;
- `primary_defensive_zz500` for the more realistic default if drawdown and cost robustness matter.

Keep `primary_ps_filtered_defensive_zz500` as a defensive diagnostic lane. Keep `safer_defensive_zz500` only as an ultra-defensive reference unless the next stage explicitly needs a low-drawdown benchmark.
