# CN ETF Margin-Positioning Source Readiness Design

## Objective

Determine whether exchange-reported margin-financing and securities-lending
detail can support a point-in-time CN ETF positioning family that is distinct
from closed price, liquidity, volatility, peer-dislocation, fund-share, and
option-sentiment directions.

## Economic mechanism

ETF-level financing balances and financing purchases measure leveraged demand
in the traded fund itself. Changes in that demand may identify crowded
positioning or exhaustion after controlling for ETF return, volatility,
liquidity, size, and venue. This differs from the previously rejected CN-stock
margin-credit family because the security being financed is the ETF and the
cross-section is the investable ETF universe. Any later prescreen must still
include direct residual and reference-duplication gates.

## Point-in-time source

Use Tushare `margin_detail`, which reports exchange-aggregated daily
financing/lending detail and is updated after the source trading day. Each
source observation dated `t` receives `available_date` equal to the next
validated CN market session. Same-day signal joins are forbidden.

Download only validated sessions from 2020-01-02 through 2024-06-28. Intersect
each response with the same-date fingerprinted CN ETF bar universe before
writing canonical evidence. Read one subsequent calendar session only to
derive `available_date`; do not read 2026 or the final holdout.

## Readiness gate

The source is ready only when:

- every canonical symbol-date maps to a same-date CN ETF bar;
- keys are unique and every `available_date` is the exact next CN session;
- at least 50 marginable ETFs exist on at least 95% of analysis sessions;
- at least 95% of rows have a positive financing balance;
- at least 99% of required numeric cells are non-missing and non-negative;
- no row enters the final holdout.

Source readiness is not alpha evidence. If ready, the only next step is a new
hash-bound preregistration with a compact primary hypothesis and explicit
residual/duplication controls.

## Data and execution safety

Canonical data and detailed reports remain under ignored `data/` paths. Git
stores only code, config, tests, hashes, and lightweight reports. No factor
generation, forward returns, portfolio grid, walk-forward, final holdout,
paper signal, broker, account, order, or live execution is allowed in this
stage.
