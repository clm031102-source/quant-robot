# Laptop Overnight Research Summary - 2026-06-16 07:00 Target

This note summarizes safe laptop work on
`codex/factor-batch-moneyflow-alpha`. The run stayed inside the
research-to-paper boundary: no broker connection, no live account read,
no order placement, no automatic live trading, and no token serialization.

All detailed artifacts under `data/reports/laptop_overnight_20260616_0700/`
are local-only and must not be committed. This document is the lightweight
Git-safe summary.

## Scope

- Machine: laptop.
- Task type: factor smoke, factor review, data-quality audit, and framework
  cleanup.
- Source: Tushare through the local secret loader; token readability was
  checked without printing the token.
- Market: CN A-shares.
- Date range for live provider smoke: 2024-12-27 to 2024-12-31.
- Open trade dates observed: 20241227, 20241230, 20241231.
- Final local provider-smoke artifact:
  `data/reports/laptop_overnight_20260616_0700/provider_smoke_20241227_20241231_fieldmissing_20260616_0050/`.
- Final local alpha-smoke artifacts:
  `data/reports/laptop_overnight_20260616_0700/alpha_smoke_moneyflow_20241227_20241231_20260616_0055/`
  and
  `data/reports/laptop_overnight_20260616_0700/alpha_smoke_daily_basic_20241227_20241231_20260616_0100/`.
- Capacity-control local artifact:
  `data/reports/laptop_overnight_20260616_0700/alpha_smoke_moneyflow_capacity_20241227_20241231_20260616_0105/`.

## Data Interfaces

| Interface | Market | Date Range | Trade Dates | Rows | Assets | Duplicates | Missing Numeric | Zero Volume | Extreme Returns | Stale Price | Adj-Close Jumps |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| daily | CN | 2024-12-27 to 2024-12-31 | 3 | 16,107 | 5,374 | 0 | 0 | 0 | 0 | 3 | 0 |
| daily_basic | CN | 2024-12-27 to 2024-12-31 | 3 | 16,107 | 5,374 | 0 | 13,042 | n/a | n/a | n/a | n/a |
| moneyflow | CN | 2024-12-27 to 2024-12-31 | 3 | 15,318 | 5,111 | 0 | 0 | n/a | n/a | n/a | n/a |

The initial live smoke showed that a range-level `adj_factor` request only
returned 6,000 rows and matched 5,916 of 16,107 daily bars, for 36.73%
coverage. That is not safe for adjusted-close research. The ingest pipeline
now falls back to trade-date `adj_factor` requests when range coverage is
partial, and still requires 100% bar-level coverage before using adjusted
close. The verified rerun fetched 16,238 fallback adjustment rows and matched
all 16,107 daily bars.

`daily_basic` field-level missingness in the final smoke:

| Field | Missing Rows |
| --- | ---: |
| pe_ttm | 4,231 |
| dv_ttm | 4,207 |
| pe | 3,247 |
| dv_ratio | 1,227 |
| pb | 100 |
| ps_ttm | 14 |
| ps | 9 |
| volume_ratio | 7 |

Moneyflow numeric fields had zero missing rows in this smoke. This makes the
moneyflow family cleaner for the next validation pass than valuation or
dividend fields, although the sample here is far too short for edge claims.

## Framework Progress

- Added a compact Tushare provider-smoke runner:
  `scripts/run_tushare_provider_smoke.py`.
- Added `fetch_adj_factor_by_trade_date` to the Tushare adapter.
- Changed daily ingest so partial adjusted-factor coverage is audited and
  triggers a trade-date fallback before adjusted close is accepted.
- Added `adjustment_report` with coverage, matched rows, missing rows,
  duplicate adjustment keys, and fallback metadata.
- Added column-level missing numeric counts for `daily_basic` and `moneyflow`
  ingest reports.
- Hardened `map_tushare_adj_factor` so empty provider responses return a
  standard empty frame instead of failing with missing-column errors.
- Added UTF-8 BOM tolerance for experiment-grid and paper-batch JSON configs.
- Added long-short and quantile-spread summary fields to experiment
  leaderboards.
- Filtered external Tushare factor inputs to the requested paper-simulation
  window before factor computation.
- Blocked alpha-factory paper candidates when the backtest reports
  capacity-limited trades.
- Exposed alpha-factory CLI controls for `--min-trades`,
  `--min-ic-observations`, `--min-long-short-observations`,
  `--portfolio-value`, `--market-impact-bps`,
  `--max-participation-rate`, and explicit capacity-control relaxation.
- Exposed the same capacity controls on the Tushare alpha-factory gate and
  passed them through to the alpha factory runner.
- Hardened Alpha Factory defaults to require 30 trades, 20 IC observations,
  20 long-short observations, nonzero market impact, and an explicit
  participation cap before any row can be treated as paper-eligible.
- Made paper-batch candidate loading fail fast with a clear missing
  leaderboard error.
- Ran the broader local workflow suite with
  `python scripts\run_checks.py --execute`; it passed while keeping the
  Tushare activation gate in dry-run mode and leaving live/paper continuation
  blocked where current data-gap, observation-history, and risk guardrails
  require more evidence.

## Factor Set

Moneyflow factors:

- `net_mf_amount_ratio`: net moneyflow amount divided by total order flow;
  broad net buying-pressure proxy.
- `net_mf_amount_ratio_low`: opposite direction of broad net moneyflow;
  tests whether weak/negative flow is rewarded.
- `large_order_net_amount_ratio`: large plus extra-large buy minus sell
  amount divided by total flow; large-order accumulation proxy.
- `large_order_net_amount_ratio_low`: opposite direction of large-order
  accumulation.
- `extra_large_order_net_amount_ratio`: extra-large buy minus sell amount
  divided by total flow; strongest order-imbalance proxy.
- `extra_large_order_net_amount_ratio_low`: opposite direction of extra-large
  order imbalance.
- `small_order_sell_pressure`: small-order sell minus buy amount divided by
  total flow; retail sell-pressure or capitulation proxy.
- `small_order_sell_pressure_low`: opposite direction of small-order sell
  pressure.

Daily-basic factors:

- `turnover_rate` and `turnover_rate_f`: liquidity/attention proxies.
- `turnover_rate_low` and `turnover_rate_f_low`: low-turnover variants.
- `volume_ratio` and `volume_ratio_low`: abnormal volume and its opposite
  direction.
- `pe_ttm_inverse`, `pb_inverse`, and `ps_ttm_inverse`: valuation yield
  proxies.
- `dv_ttm`: trailing dividend yield proxy.
- `total_mv_log` and `circ_mv_log`: size and free-float size proxies.

## Moneyflow Alpha Smoke

This smoke used `top_n=1`, `cost_bps=5`, `execution_lag=1`, and only one IC
observation. All eight hypotheses completed; all eight were rejected after
multiple-testing correction; paper-eligible count was 0. This is a pipeline
and data-quality smoke only, not profit evidence.

| Factor | IC | RankIC | IC+ | Adj p | LS Mean | Q Spread | Costed Return | Turnover | Max DD | Trades | Sample | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| extra_large_order_net_amount_ratio_low | -0.0466 | -0.0312 | 0.00 | 1.00 | -0.0035 | -0.0035 | -0.1010 | 1.00 | 0.0000 | 1 | 1 | reject |
| extra_large_order_net_amount_ratio | 0.0466 | 0.0312 | 1.00 | 1.00 | 0.0026 | 0.0026 | 0.0438 | 1.00 | 0.0000 | 1 | 1 | reject |
| large_order_net_amount_ratio_low | -0.0499 | -0.0143 | 0.00 | 1.00 | -0.0015 | -0.0015 | -0.1010 | 1.00 | 0.0000 | 1 | 1 | reject |
| large_order_net_amount_ratio | 0.0499 | 0.0143 | 1.00 | 1.00 | 0.0015 | 0.0015 | 0.0491 | 1.00 | 0.0000 | 1 | 1 | reject |
| net_mf_amount_ratio_low | -0.1220 | -0.2212 | 0.00 | 1.00 | -0.0079 | -0.0079 | 0.0491 | 1.00 | 0.0000 | 1 | 1 | reject |
| net_mf_amount_ratio | 0.1220 | 0.2212 | 1.00 | 1.00 | 0.0079 | 0.0079 | -0.1010 | 1.00 | 0.0000 | 1 | 1 | reject |
| small_order_sell_pressure_low | -0.0046 | 0.0352 | 0.00 | 1.00 | 0.0003 | 0.0003 | -0.0510 | 1.00 | 0.0000 | 1 | 1 | reject |
| small_order_sell_pressure | 0.0046 | -0.0352 | 1.00 | 1.00 | -0.0003 | -0.0003 | 0.0487 | 1.00 | 0.0000 | 1 | 1 | reject |

Several one-trade rows report positive costed returns, but those are rejected
because the sample has only one IC observation, p-values are 1.0 after
multiple-testing adjustment, and some rows imply impossible capacity at the
configured capital size.

The capacity-control rerun used `market_impact_bps=10`,
`max_participation_rate=0.05`, and `portfolio_value=1000000`. Four of eight
moneyflow rows recorded `capacity_limited_trades=1` and included
`capacity_limited_trades_present` in the paper-candidate rejection reasons.

## Daily-Basic Alpha Smoke

This smoke used the same `top_n=1`, `cost_bps=5`, and `execution_lag=1`
settings. The first command timed out at 120 seconds and left a partial
local-only directory. A non-overwriting rerun completed in
`alpha_smoke_daily_basic_20241227_20241231_20260616_0100/`.

All 12 hypotheses completed; all 12 were rejected after multiple-testing
correction; paper-eligible count was 0. This is a pipeline smoke only.

| Factor | IC | RankIC | IC+ | Adj p | LS Mean | Q Spread | Costed Return | Turnover | Max DD | Trades | Sample | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| circ_mv_log | -0.0946 | -0.1144 | 0.00 | 1.00 | -0.0066 | -0.0066 | -0.0017 | 1.00 | 0.0000 | 1 | 1 | reject |
| dv_ttm | 0.2013 | 0.2959 | 1.00 | 1.00 | 0.0095 | 0.0095 | -0.0148 | 1.00 | 0.0000 | 1 | 1 | reject |
| pb_inverse | 0.0778 | 0.1470 | 1.00 | 1.00 | 0.0049 | 0.0049 | -0.0510 | 1.00 | 0.0000 | 1 | 1 | reject |
| pe_ttm_inverse | 0.1526 | 0.2779 | 1.00 | 1.00 | 0.0089 | 0.0089 | 0.0194 | 1.00 | 0.0000 | 1 | 1 | reject |
| ps_ttm_inverse | 0.0470 | 0.1726 | 1.00 | 1.00 | 0.0062 | 0.0062 | -0.0389 | 1.00 | 0.0000 | 1 | 1 | reject |
| total_mv_log | -0.1029 | -0.1530 | 0.00 | 1.00 | -0.0083 | -0.0083 | -0.0053 | 1.00 | 0.0000 | 1 | 1 | reject |
| turnover_rate_f_low | 0.1680 | 0.2723 | 1.00 | 1.00 | 0.0076 | 0.0076 | 0.0487 | 1.00 | 0.0000 | 1 | 1 | reject |
| turnover_rate_f | -0.1680 | -0.2723 | 0.00 | 1.00 | -0.0077 | -0.0077 | -0.0878 | 1.00 | 0.0000 | 1 | 1 | reject |
| turnover_rate_low | 0.1888 | 0.2919 | 1.00 | 1.00 | 0.0081 | 0.0081 | 0.0491 | 1.00 | 0.0000 | 1 | 1 | reject |
| turnover_rate | -0.1888 | -0.2919 | 0.00 | 1.00 | -0.0081 | -0.0081 | 0.0182 | 1.00 | 0.0000 | 1 | 1 | reject |
| volume_ratio_low | 0.0819 | 0.0629 | 1.00 | 1.00 | 0.0028 | 0.0028 | 0.0491 | 1.00 | 0.0000 | 1 | 1 | reject |
| volume_ratio | -0.0819 | -0.0629 | 0.00 | 1.00 | -0.0027 | -0.0027 | -0.0998 | 1.00 | 0.0000 | 1 | 1 | reject |

## Classification

- Candidate: none.
- Observe: the data pipeline and moneyflow factor family are worth further
  validation because moneyflow coverage was clean in the smoke and no numeric
  fields were missing.
- Reject for promotion: every factor row in the 3-day moneyflow and
  daily-basic alpha smokes.
- Unable to judge: full-year profitability, walk-forward robustness,
  post-cost capacity, regime stability, listing-status coverage, and
  survivorship effects.

## Risk Judgment

- Smoke results are not profit proof.
- Future-function risk remains open until data-vintage and alignment are
  audited end to end, even though these experiments use `execution_lag=1`.
- Overfitting and multiple-testing risk are material. Bonferroni-adjusted
  p-values are necessary but not sufficient.
- Sample size is intentionally tiny here: one IC observation and one trade per
  factor. Annualized return and Sharpe values from this smoke must be ignored.
- Transaction-cost and liquidity risk remain material. Some single-trade smoke
  rows show participation rates above realistic limits.
- Alpha-factory promotion now blocks rows with capacity-limited trades, but
  broader liquidity and market-impact calibration still needs more data.
- Survivorship and listing-status bias remain possible in the CN universe.
- `daily_basic` valuation and dividend fields have substantial missingness;
  factor families using those fields need field-level null policies before
  promotion.
- A range-level `adj_factor` request can silently under-cover the universe;
  the new fallback and audit report are required before trusting adjusted
  close.

## Next Work

1. Rerun the provider smoke on longer but still bounded monthly or quarterly
   windows with the adjusted-factor fallback.
2. Rebuild any previously generated adjusted-close datasets that were created
   before the fallback fix.
3. Prefer moneyflow candidates for the next validation batch because this
   smoke showed cleaner field coverage than valuation/dividend fields.
4. Add liquidity/capacity guards to alpha-factory candidate ranking before
   interpreting costed returns.
5. Run out-of-sample and walk-forward validation before labeling any factor a
   profit candidate.
