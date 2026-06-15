# Laptop Overnight Research Summary - 2026-06-16 07:00 Target

This note summarizes safe laptop work on
`codex/factor-batch-moneyflow-alpha`. The run stayed inside the
research-to-paper boundary: no broker connection, no live account read,
no order placement, no automatic live trading, and no token serialization.
Detailed artifacts under `data/reports/laptop_overnight_20260616_0700/`
are local-only and must not be committed.

## Scope

- Machine: laptop.
- Task type: low-load factor smoke, data-quality audit, and framework
  cleanup.
- Source: Tushare through the local secret loader.
- Market: CN A-shares.
- Local output directory: `data/reports/laptop_overnight_20260616_0700/`.
- Commit-safe outputs: this markdown summary plus a small data-quality
  audit repair-action fix and tests.

## Provider Smoke

The live provider smoke covered 2024-12-27 to 2024-12-31, with open
trade dates 20241227, 20241230, and 20241231. It used `trade_cal`,
`daily`, `daily_basic`, and `moneyflow`, with about 10 provider calls.
No raw row-level provider data was serialized into the summary artifacts.

| Interface | Rows | Max assets | Duplicates | Missing numeric | Zero volume | Extreme intraday range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| daily | 16,107 | 5,370 | 0 | 0 | 0 | 0 |
| daily_basic | 16,107 | 5,370 | 0 | 13,042 | n/a | n/a |
| moneyflow | 15,318 | 5,107 | 0 | 0 | n/a | n/a |

The `daily_basic` missing-numeric count needs field-level interpretation.
It is not treated as an immediate provider failure, but it blocks any
strong claim until the missing fields are mapped to optional valuation
columns versus unexpected gaps.

## Data Quality

The local processed-bar audit used existing data under
`data/processed/tushare_alpha_factory_gate/`.

| Dataset | Rows | Assets | Range | Duplicates | Missing date rows | Zero volume | Other quality flags |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| OHLCV processed bars | 1,288,559 | 5,433 | 2024-01-02 to 2024-12-31 | 0 | 1,352 gap-audit rows | 0 | 3,502 extreme returns; 3,950 stale-price rows; 3,552 adjusted-close jumps |
| Moneyflow inputs | 1,223,005 | 5,170 | 2024-01-02 to 2024-12-31 | 0 | n/a | n/a | 0 missing asset IDs; 0 missing numeric rows |

The fresh gap audit found 283 assets with gaps across 1,352 missing
date rows. These gaps should be reviewed against listing status,
suspensions, and provider coverage before promoting any signal.

## Factor Set

- `net_mf_amount_ratio`: net moneyflow amount divided by total flow;
  proxy for broad net buying pressure.
- `net_mf_amount_ratio_low`: the negative of net moneyflow ratio;
  tests whether low or negative flow is rewarded.
- `large_order_net_amount_ratio`: large plus extra-large buy minus sell
  amount divided by total flow; proxy for large-order accumulation.
- `large_order_net_amount_ratio_low`: the opposite direction of
  large-order accumulation.
- `extra_large_order_net_amount_ratio`: extra-large buy minus sell
  amount divided by total flow; proxy for the strongest order imbalance.
- `extra_large_order_net_amount_ratio_low`: the opposite direction of
  extra-large order imbalance.
- `small_order_sell_pressure`: small-order sell minus buy amount divided
  by total flow; proxy for retail sell pressure or capitulation.
- `small_order_sell_pressure_low`: the opposite direction of small-order
  sell pressure.

## Full-Year Moneyflow Results

Existing full-year alpha-factory evidence covered 2024-01-02 to
2024-12-31, market CN, `top_n=1`, `cost_bps=5`, and `execution_lag=1`.
All 8 hypotheses completed. All 8 passed adjusted IC p-value checks in
the full-year run, and 4 were paper-eligible. This is research evidence,
not production approval.

| Factor | IC | RankIC | IC+ rate | IC t-stat | Adj p-value | Total return | Long-short mean | Turnover | Max DD | Paper result | Tier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| extra_large_order_net_amount_ratio | 0.016538 | -0.004939 | 0.611814 | 4.928648 | 0.000007 | 371.162831 | 0.013973 | 1.0 | -0.678292 | passed | observe |
| small_order_sell_pressure | 0.013066 | -0.008306 | 0.607595 | 2.910471 | 0.028871 | 27.282530 | 0.008393 | 1.0 | -0.630129 | passed | observe |
| net_mf_amount_ratio_low | 0.027620 | 0.009662 | 0.603376 | 4.458233 | 0.000066 | 443.427026 | -0.004561 | 1.0 | -0.558398 | passed | observe |
| large_order_net_amount_ratio | 0.018624 | -0.006433 | 0.662447 | 5.102630 | 0.000003 | 374.571608 | 0.010353 | 1.0 | -0.348784 | passed | observe |
| extra_large_order_net_amount_ratio_low | -0.016538 | 0.004939 | 0.388186 | -4.928648 | 0.000007 | -1.000282 | -0.016538 | 1.0 | -1.000942 | skipped | reject |
| net_mf_amount_ratio | -0.027620 | -0.009662 | 0.396624 | -4.458233 | 0.000066 | -0.998404 | 0.004561 | 1.0 | -0.999690 | skipped | reject |
| large_order_net_amount_ratio_low | -0.018624 | 0.006433 | 0.337553 | -5.102630 | 0.000003 | -1.000141 | -0.010352 | 1.0 | -1.001279 | skipped | reject |
| small_order_sell_pressure_low | -0.013066 | 0.008306 | 0.392405 | -2.910471 | 0.028871 | -0.999625 | -0.008394 | 1.0 | -0.999905 | skipped | reject |

The paper batch passed the four observe-tier factors under defensive or
balanced paper profiles, with modeled commission, slippage, market impact,
participation caps, and risk profile constraints. This should remain
observation evidence only because the full-year drawdowns and extreme
reported strategy returns are not robust enough for promotion.

## December 2024 Capacity Smoke

A low-load smoke reran the same 8 moneyflow hypotheses on 2024-12-02 to
2024-12-31 with `top_n=1`, `cost_bps=5`, `market_impact_bps=10`, and
`max_participation_rate=0.05`. All 8 experiments completed, but none
survived adjusted IC significance. Paper-eligible count was 0.

| Factor | IC | RankIC | IC+ rate | IC t-stat | Adj p-value | Total return | Turnover | Avg cost | Capacity-limited trades | Max DD | Tier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| extra_large_order_net_amount_ratio | 0.019991 | -0.019433 | 0.65 | 1.772534 | 0.610448 | 6.652149 | 1.0 | 0.002035 | 7 | -0.150421 | reject |
| large_order_net_amount_ratio | 0.017915 | -0.018007 | 0.65 | 1.616930 | 0.847146 | 8.285571 | 1.0 | 0.002146 | 9 | -0.151926 | reject |
| small_order_sell_pressure | 0.008057 | -0.022376 | 0.65 | 0.839180 | 1.0 | 1.681294 | 1.0 | 0.001915 | 8 | -0.306623 | reject |
| net_mf_amount_ratio_low | 0.020450 | 0.019815 | 0.60 | 1.317142 | 1.0 | 6.855665 | 1.0 | 0.001860 | 5 | -0.129484 | reject |

This is explicitly a smoke test, not profit proof. The sample has only
20 IC observations and 18 to 20 trades per factor. Short-window
annualized returns and Sharpe ratios are distorted and should not be used
as evidence of economic edge.

## Framework Progress

- Fixed the data-quality gap-audit repair action so follow-up commands
  use the audited market instead of always recommending `CN_ETF`.
- Added a regression test for CN repair-command generation.
- Produced local-only provider smoke and capacity-smoke artifacts in a
  timestamped report directory.
- Converted the local research evidence into a commit-safe summary that
  can be pulled by the office desktop.

## Classification

- Production candidates: none.
- Paper-only observation candidates: `extra_large_order_net_amount_ratio`,
  `small_order_sell_pressure`, `net_mf_amount_ratio_low`, and
  `large_order_net_amount_ratio`.
- Rejected or deprioritized: the four opposite-direction variants from
  the full-year run, plus all December capacity-smoke rows for paper
  eligibility because adjusted IC p-values failed after multiple testing.
- Undetermined: `daily_basic` missing numeric fields, OHLCV missing-date
  gaps, listing/suspension coverage, and broader regime behavior.

## Profit-Oriented Project Plan

The next project steps should move from "interesting signal" toward
"possibly monetizable system" in this order:

1. Data trust: reconcile missing-date rows, stale prices, adjusted-close
   jumps, and optional versus unexpected `daily_basic` null fields.
2. Signal trust: rerun observe-tier factors across walk-forward splits,
   regimes, and at least one out-of-sample period.
3. Cost and capacity trust: model spread, impact, participation caps,
   turnover, and liquidity filters before paper promotion.
4. Portfolio trust: compare single-name `top_n=1` artifacts against
   diversified profiles with drawdown and concentration limits.
5. Paper observation: keep candidates paper-only until sample size,
   drawdown, turnover, and execution assumptions survive repeated checks.
6. Live boundary: do not add broker, account, or order code until the
   research gates above are green and manually approved.

## Risk Judgment

- Smoke results are not profit proof.
- Future-function risk remains open until data-vintage and alignment are
  audited end to end, even though the experiments use `execution_lag=1`.
- Overfitting and multiple-testing risk are material; Bonferroni-adjusted
  p-values are necessary but not sufficient.
- Sample size is weak for the December smoke and only one calendar year
  is available in the current full-year report.
- Transaction-cost and liquidity risk are material. Several December
  smoke trades hit the 5 percent participation cap.
- Survivorship and listing-status bias remain possible in the CN universe.
- Data-quality gaps and missing `daily_basic` numeric fields block any
  promotion claim.

## Next Work

- Reconcile the 1,352 missing-date rows against listing status and
  suspensions.
- Rerun walk-forward or out-of-sample validation before treating any
  observe-tier factor as a real candidate.
- Keep all generated `data/reports/laptop_overnight_20260616_0700/`
  artifacts local-only.
