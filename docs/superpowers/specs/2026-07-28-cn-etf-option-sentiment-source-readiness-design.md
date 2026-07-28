# CN ETF Option-Sentiment Source Readiness Design

## Objective

Determine whether exchange-traded option metadata and daily contract activity
can support a new primary CN ETF cross-sectional family without reusing closed
price, liquidity, volatility, peer-dislocation, or fund-share directions.

## Source

Use Tushare `opt_basic` for contract identity and `opt_daily` for historical
daily close, volume, amount, and open interest. The documented permission
requirements are 5,000 points for contract metadata and 2,000 points for daily
data. Both endpoints must be probed with the configured local credential
without recording the credential.

Contract metadata is filtered to contracts overlapping the frozen 2020-01-02
through 2024-06-28 analysis period. Representative daily probes are frozen at
2020-01-02, 2021-01-04, 2022-01-04, 2023-01-03, and 2024-06-28 for both SSE
and SZSE.

## Readiness gate

A primary cross-sectional family requires at least 30 distinct ETF
underlyings, daily option rows on every probe date, valid call/put identity,
and at least 95% positive option closes on each probe. Contract and daily
source rows are never treated as alpha evidence.

If fewer than 30 ETF underlyings exist, the family is structurally blocked:
the source may later be retained as a market-regime or risk-control input, but
it cannot receive primary cross-sectional budget and no factor batch is
allowed.

## Safety

No factor values, forward returns, portfolio grid, walk-forward, holdout,
paper signal, broker access, account access, orders, or live trading.
