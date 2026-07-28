# CN ETF Option-Sentiment Source Readiness

Date: 2026-07-28

## Decision

The Tushare option source is technically accessible and internally consistent,
but it is structurally blocked for a primary CN ETF cross-sectional factor
family. Only nine ETF underlyings overlap the frozen 2020-01-02 through
2024-06-28 analysis window, below the preregistered minimum of 30.

No factor values or forward returns were generated. No prescreen authorization
was created or consumed.

## Source contract

- Contract metadata: Tushare `opt_basic`, SSE and SZSE
- Daily activity: Tushare `opt_daily`, SSE and SZSE
- Contract fields: code, exchange, ETF option code, call/put identity, listing
  date, and delisting date
- Daily fields: contract, trade date, exchange, close, volume, amount, and open
  interest
- Frozen probe dates: 2020-01-02, 2021-01-04, 2022-01-04, 2023-01-03, and
  2024-06-28
- Official API references:
  [opt_basic](https://tushare.pro/document/2?doc_id=158) and
  [opt_daily](https://tushare.pro/document/2?doc_id=159)

The configured credential was read locally and was not recorded in any
artifact.

## Evidence

The analysis-overlap metadata contains 9,346 unique option contracts:

| Exchange | ETF underlyings |
| --- | ---: |
| SSE | 5 |
| SZSE | 4 |
| Total | 9 |

The distinct underlyings are `510050.SH`, `510300.SH`, `510500.SH`,
`588000.SH`, `588080.SH`, `159901.SZ`, `159915.SZ`, `159919.SZ`, and
`159922.SZ`.

All five combined exchange-date probes were present. Contract mapping was
100% on every probe. Positive-close ratios ranged from 97.038724% to 100%:

| Date | Rows | Positive close | Contract mapping |
| --- | ---: | ---: | ---: |
| 2020-01-02 | 328 | 100.000000% | 100.000000% |
| 2021-01-04 | 364 | 100.000000% | 100.000000% |
| 2022-01-04 | 342 | 97.953216% | 100.000000% |
| 2023-01-03 | 730 | 97.123288% | 100.000000% |
| 2024-06-28 | 878 | 97.038724% | 100.000000% |

The source therefore passes the bounded availability and daily-quality checks,
but fails the only breadth blocker:
`etf_option_underlying_count_below_minimum`.

## Reproducibility

Two independent CLI runs produced identical outputs after contract-column
ordering was made deterministic.

- Config SHA-256:
  `d0c2a95f2bde767ceb181cfe01b881eedab5c493f7253eb9ba42274dfe6a1deb`
- Readiness JSON SHA-256:
  `0c889a9bea6f583947c3faac60cb2175c643966fde8dadad9deef9df46ee8739`
- Contracts SHA-256:
  `0329d9a568e4437561bc6e6a1d9ebcf008aa426de0f100240ecf2077ed13bfc3`
- Daily rows SHA-256:
  `bf30db5fbf794edd1d4c483851d84f4cb7bcd4f1b16a358d47fbc2dab6e8e145`
- Underlyings SHA-256:
  `2268cbc3027a9c4241e53d9369ad8fcd5dad3b465b7d649f896646c0bff5b82b`
- Probe summary SHA-256:
  `481133ff268bf2b8dce606678f1325ab143d30ea3f0420a29b5dd7f0afcd49a8`

Detailed evidence remains under ignored
`data/reports/cn_etf_option_sentiment_source_readiness_20260728/`.

## Scheduler and next action

`cn_etf_option_sentiment` remains exploratory with zero primary budget. Its
audited data may later be used only as a market-regime or risk-control input,
where nine broad ETF underlyings can still be economically meaningful.

Do not generate a primary option-sentiment cross-sectional factor, read forward
returns, run a factor batch, tune parameters, access the final holdout, or open
paper/live execution boundaries. Rotate to another genuinely orthogonal CN ETF
source family.

