# CN ETF External Data Unlock Review

Date: 2026-07-28

## Decision

The project does not currently have a validated money-making CN ETF strategy.
After the fund-structure, option-sentiment, and margin-positioning paths were
closed or blocked, this review tested the shortest genuinely orthogonal data
route without generating a factor or reading a forward return.

The highest-value next action is:

`unlock_historical_pcf_first`

The local Tushare credential can access historical index weights and current
exchange-traded fund metadata, but it cannot access either exchange's
historical daily ETF PCF/constituent endpoint or the structured ETF-to-index
mapping endpoint. The blocked endpoints share an official 8,000-point
requirement.

## Reproducible access result

| Route | Endpoint | Probe | Result |
| --- | --- | ---: | --- |
| Historical ETF PCF | `etf_sh_cons` | 510050.SH on 2020-01-02 | permission denied |
| Historical ETF PCF | `etf_sh_cons` | 510050.SH on 2024-06-28 | permission denied |
| Historical ETF PCF | `etf_sz_cons` | 159919.SZ on 2020-01-02 | permission denied |
| Historical ETF PCF | `etf_sz_cons` | 159919.SZ on 2024-06-28 | permission denied |
| ETF-to-index mapping | `etf_basic` | all active ETFs | permission denied |
| Fund metadata | `fund_basic` | active exchange-traded funds | ready, 2,154 rows |
| Historical index constituents | `index_weight` | CSI 300, January 2020 | ready, 300 rows |

The four PCF probes deliberately cover both exchanges and both ends of the
frozen research period. A successful probe would still be access evidence only,
not source readiness. Full backfill, fingerprinting, point-in-time alignment,
coverage checks, and duplicate/schema audits remain mandatory before any factor
is defined.

Generated evidence:

- config SHA-256:
  `c2fdc6b14c8e2f18bc802bafcf3b374012dffdab8119ff068f1c21cf284470e0`
- result SHA-256:
  `1228366e935fb5f197f3377a5f9e1d3f5d6d76f16b4233c8207454c9fccb573d`
- probe table SHA-256:
  `4c9c62bc29eac4817dfa9731cb3ccd055eee33b4a24b27d27a46126978be616d`

Detailed evidence remains under ignored
`data/reports/cn_etf_external_data_unlock_review_20260728/`.

## Why PCF is the first purchase

Daily PCF data supplies the actual creation/redemption basket, constituent
quantities, cash-substitution flags, and substitution premium/discount terms.
It is economically different from the already closed daily price, liquidity,
volatility, fund-share, option, and margin families. It can support tests of
basket pressure, substitution stress, and ETF-versus-basket dislocation without
reviving those old names.

Official source definitions:

- [Tushare SSE daily ETF PCF](https://tushare.pro/document/2?doc_id=471)
- [Tushare SZSE daily ETF PCF](https://tushare.pro/document/2?doc_id=472)
- [Tushare ETF-to-index metadata](https://tushare.pro/document/2?doc_id=385)
- [Tushare index constituents and weights](https://tushare.pro/document/2?doc_id=96)

The exchange websites publish current daily PCF information, but this review
did not establish a complete, programmatically retrievable historical archive
for both exchanges. Current files are not a substitute for the frozen
2020-01-02 through 2024-06-28 history.

## Minimum acceptable delivery

Either of the following unblocks the next work:

1. Enable the local Tushare account for `etf_sh_cons`, `etf_sz_cons`, and
   preferably `etf_basic`; or
2. provide a licensed vendor export covering both exchanges from 2020-01-02
   through 2024-06-28.

The vendor export must contain, at minimum:

- trade date;
- ETF code;
- constituent code;
- constituent quantity;
- cash-substitution flag;
- subscription premium or guarantee rate;
- redemption discount or guarantee rate;
- subscription/redemption cash-substitution amounts where supplied;
- exchange/source identity and a data dictionary.

Preferred delivery is Parquet partitioned by date or year. CSV is acceptable.
Files must be historical snapshots, not a present-day constituent list applied
backward.

## Secondary unlocks

1. Historical point-in-time ETF-to-index mapping. The local account can already
   retrieve monthly index constituents, so the missing part is the dated ETF
   mapping. Current `fund_basic.benchmark` text is useful for review but is not
   accepted as a complete historical mapping.
2. Historical ETF IOPV/premium minute data. Tushare documents
   `rt_etf_sz_iopv` as a current Shenzhen-only, separately permissioned feed;
   it does not document the historical archive needed here.
3. Authoritative replacement ETF bars for 2020-05-28 and 2020-06-03. Those two
   official sessions remain absent from the current ETF bar authority and must
   be repaired or formally adjudicated before promotion.

## Boundary

This review read no factor matrix, forward return, portfolio result,
walk-forward fold, final holdout, paper signal, broker, account, or order data.
It authorizes data acquisition and source auditing only.
