# CN ETF Margin-Positioning Source Readiness

Date: 2026-07-28

## Decision

The point-in-time CN ETF margin-positioning source is
`ready_for_margin_positioning_preregistration`.

This is source readiness, not alpha evidence. No factor, forward return,
portfolio grid, walk-forward, final-holdout read, paper signal, or live action
was performed.

## Economic and source scope

Tushare `margin_detail` provides daily exchange-aggregated financing and
securities-lending fields. The official documentation states that the prior
day is updated around 08:30 and that fund units are represented in the lending
quantity fields. Every source date is therefore assigned to the exact next
validated CN session before it can join a signal.

The mechanism is ETF-specific leveraged positioning. It does not reuse the
closed CN-stock raw margin-credit signal: any later ETF prescreen must
residualize return, volatility, liquidity, size, and venue and explicitly test
the prior stock-family residual failure as a duplication reference.

Official API reference:
[margin_detail](https://tushare.pro/document/2?doc_id=59).

## Frozen evidence

- Analysis source dates: 2020-01-02 through 2024-06-28
- Validated calendar sessions: 1,087
- Observed and qualifying source dates: 1,085
- Canonical rows: 199,793
- Distinct marginable ETFs/funds: 410
- Median assets per observed date: 183
- Maximum assets per observed date: 297
- Qualifying date coverage at the 50-asset gate: 99.816007%
- Positive financing-balance ratio: 99.960459%
- Valid, non-missing, non-negative numeric-cell ratio: 99.956017%
- Exact next-session availability ratio: 100%
- Same-date ETF-bar intersection ratio: 100%
- Duplicate keys: 0
- Final-holdout rows: 0

The local cache contains one resumable shard for each of the 1,087 requested
sessions. A cache-only rerun reproduced all five yearly canonical file hashes
and all report hashes.

## ETF bar-authority constraint

The official calendar contains 2020-05-28 and 2020-06-03, and Tushare returns
1,779 and 1,780 market-wide margin-detail rows on those dates respectively.
The local CN ETF bar authority contains zero rows on both dates. These are bar
authority gaps, not source gaps.

The two dates therefore contribute no canonical ETF rows. Any preregistration
must exclude factor or label windows crossing these sessions, and promotion
remains forbidden until the bar gaps are repaired or independently adjudicated.

## Reproducibility

- Config SHA-256:
  `0b0760536cd779e90bc9b4af607ef6ce0441f9f948369006dedcbbbb47c30c22`
- Readiness JSON SHA-256:
  `8c61c7b147046bfd6c4a33f832e8c77bcd732d51b52c98b0aa9be5a6e0a3f2d5`
- Manifest SHA-256:
  `382ccf8b48bb3e64f2bf8e3b3cbe5b176791d450094e6be004b291d2938542db`
- Canonical dataset SHA-256:
  `f1152513e73bc69576d04a61585f3971cad007dc04482dbdc0e38d049d3565ec`
- Date coverage SHA-256:
  `819dd2b0f2b52cee8844acf46e919d9e0b733930347615ce939d950311147fe1`

Detailed data and source evidence remain under ignored
`data/processed/cn_etf_margin_positioning_2020_2024/` and
`data/reports/cn_etf_margin_positioning_source_readiness_20260728/`.

## Next action

Preregister exactly one compact ETF-specific margin-positioning prescreen.
Before that registration, factor generation and forward-return reads remain
disabled. The later prescreen must be authorization-bound, cost-aware, capacity
aware, style-residualized, duplication-gated, and unable to access the 2026
final holdout.

