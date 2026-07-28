# CN ETF Fund-Structure Crowding Prescreen Design

## Objective

Test exactly one economically motivated CN ETF fund-structure signal against the
existing cross-sectional, capacity, cost, and closed-family gates. The test must
be preregistered before any factor values or forward returns are read.

## Frozen hypothesis

Investor creations often chase recent performance. After removing observable
price, volatility, liquidity, scale, and venue exposures, an unusually large
20-session increase in ETF shares represents crowded inflow pressure. The
frozen prediction is short-horizon reversal: larger residual creations imply
lower subsequent return.

The only candidate is:

`etf_residual_share_creation_crowding_reversal_20`

Its value on signal date `d` is the negative cross-sectional OLS residual of:

`log(total_share_asof_t / total_share_asof_t_minus_20_sessions)`

where the share snapshot for source session `t` is not usable before its
recorded `known_from` session `d`. The regression controls are fixed at
20-session adjusted-close return, 60-session adjusted-close return,
20-session realized volatility, log 20-session average traded amount, log
fund size, and exchange indicator. Every continuous input is winsorized at the
daily 1st/99th percentiles and standardized before OLS. A day requires at least
30 eligible finite observations and full rank.

## Data and point-in-time boundary

- Analysis period: 2020-01-02 through 2024-06-28.
- Final 2026 holdout remains sealed.
- Share observations come only from the audited public SSE/SZSE canonical
  dataset. Each yearly Parquet partition, the source-readiness config, and the
  frozen source-readiness result are hash-bound.
- `known_from` must be strictly later than the share observation date.
- Price controls use information available on the signal date. Forward returns
  use the repository's one-session execution lag.
- The official point-in-time ETF lifecycle and existing liquidity/staleness
  eligibility policy remain mandatory.

## Evaluation

There are two counted hypotheses: five sessions is primary and twenty sessions
is diagnostic only. Benjamini-Hochberg correction covers both. The primary
must pass every existing statistical gate, remain strictly below the 0.85
closed-family and direct-exposure correlation ceilings, have daily capacity
support, and retain a positive long-short spread after 10 bps one-way cost.
The diagnostic horizon cannot rescue a failed primary.

## Stop rule

Only one execution is authorized by a hash-bound, one-use ledger. A primary
failure closes the family at zero budget. No sign flip, alternative window,
control removal, threshold relaxation, subgroup rescue, portfolio grid,
walk-forward, or holdout read is allowed. A primary pass authorizes only a
separately preregistered history backfill and walk-forward design.

## Safety

Research-to-paper only. No broker connection, account access, order placement,
live trading, or profit claim is authorized.
