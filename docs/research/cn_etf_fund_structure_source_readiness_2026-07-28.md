# CN ETF Fund-Structure Source Readiness

Date: 2026-07-28

Branch: `codex/factor-review-cn-etf-fund-structure-source-20260728`

Primary market: `CN_ETF`

Decision: `ready_for_fund_structure_preregistration`; no factor generation in this stage

## Executive Decision

The historical ETF share/NAV source blocker is repaired for the frozen 2020-01-02 through 2024-06-28 research window.

The current Tushare token is usable generally but the live one-session `etf_share_size` probe was explicitly denied by provider permissions. The project therefore collected dated ETF shares from the Shanghai and Shenzhen exchange endpoints, dated historical unit NAV from the public Eastmoney fund-detail payload, and closes from the existing bounded Tushare `fund_daily` bar authority.

All frozen coverage, source-identity, point-in-time, positivity, duplicate, derived-value, and holdout gates passed. This authorizes only one later compact preregistration. It does not establish alpha, profitability, portfolio readiness, or permission to run the legacy broad ETF share-size grid.

## Frozen Evidence

| Check | Result |
| --- | ---: |
| Analysis window | 2020-01-02 to 2024-06-28 |
| Analysis sessions | 1,085 |
| Bar-authority rows | 1,119,490 |
| Bar-authority ETF assets | 1,781 |
| Canonical share/NAV rows | 645,645 |
| Share-covered ETF assets | 1,023 |
| Positive NAV rows | 642,285 |
| Combined qualifying-date coverage | 100.00% |
| SSE qualifying-date coverage | 100.00% |
| SZSE qualifying-date coverage | 100.00% |
| Median daily bar-asset share coverage | 60.074627% |
| NAV intersection coverage | 99.479590% |
| Positive share ratio | 100.00% |
| Positive NAV ratio | 100.00% |
| Duplicate asset-date rows | 0 |
| Point-in-time lag violations | 0 |
| Derived scale mismatches | 0 |
| Derived premium/discount mismatches | 0 |
| Rows outside frozen window | 0 |
| Final-holdout rows | 0 |

Frozen config SHA-256: `04cb2acc675762f04c109798949d2b174fb1c9c72a9d91497423837f366a0ba3`

Readiness result SHA-256: `3ccb5ba4d04ff24b7b5ef81c2984f1571a0a23cd41f077c7b20ae688879f3a13`

Date-coverage CSV SHA-256: `b8ee350d8ece4f6a49ca4dcb6d4608c28ec02716f04de02cb39fd193386e04cb`

Generated data, provider manifests, and detailed audit artifacts remain under ignored `data/processed/cn_etf_fund_structure_public_2020_2024/` and `data/reports/cn_etf_fund_structure_source_readiness_20260728/`.

## Source And Timing Contract

- SSE shares: official dated ETF-scale endpoint, one request per observed analysis session.
- SZSE shares: official dated fund-scale workbook endpoint in 90-day windows.
- NAV: public Eastmoney fund-detail history, one response per bar-authority fund code.
- Close: bounded Tushare `fund_daily` authority.
- Scale: `total_share * nav`.
- Premium/discount: `close / nav - 1`.
- Every dated share/NAV observation becomes eligible only on the next validated CN market session.
- The official 2015-2025 Tushare SSE/SZSE calendar supplies the next-session mapping. The calendar is hash-validated before use.

The NAV source is a secondary public copy, not exchange authority. It is acceptable for a single research prescreen only because 99.48% of share/bar intersections have positive NAV, source identity is explicit, and all derived-value checks pass. Any later divergence or revision evidence must fail closed.

## Repairs Made During The Real Backfill

1. Replaced the inaccessible Tushare share/NAV entitlement with an explicit public-source adapter.
2. Added robust SSE JSON, SZSE workbook, and Eastmoney JavaScript parsing with schema, fund-identity, duplicate, and response-hash checks.
3. Preserved zero values for the readiness quality gate instead of allowing one unusable row to discard a complete exchange date.
4. Removed expensive response-encoding detection from the NAV path and decoded the ASCII/UTF-8 payload directly.
5. Added bounded Windows manifest-write retries after one transient atomic-replace denial.
6. Added resumable per-date, per-window, and per-symbol source partitions so interrupted runs did not redownload completed data.
7. Rechunked SZSE requests from near-six-month intervals to 90-day intervals after the provider returned empty data for some boundary-length windows.
8. Migrated only the SZSE request plan while preserving completed SSE and NAV evidence.
9. Normalized the bar authority's generic `tushare` source label to the semantic `tushare_fund_daily` close authority.
10. Used the validated official calendar for the next session after 2024-06-28 because the bounded bar history itself ends on that date.

## Provider Request Evidence

- SSE share requests: 1,085 completed, 0 failed.
- SZSE share requests: 19 completed, 0 failed.
- Eastmoney NAV symbols: 1,753 completed and 26 without a NAV dataset.
- The 26 missing per-symbol NAV datasets are not hidden. They are acceptable only because the frozen row-level NAV intersection gate still clears at 99.48%.
- Tushare `etf_share_size`: permission denied and non-retryable with the current token.

## Governance Decision

The `cn_etf_fund_structure` family remains at zero budget. Its scheduler state changes from source-blocked to `ready_for_preregistration`.

The Quant PM gate now permits only `factor_review` in `preregistration_only` mode. The next allowed action is to freeze exactly one compact, economically motivated fund-structure prescreen with explicit timing, multiple-testing scope, 5/10 bps costs, liquidity/capacity checks, reference-duplication gates, and a one-execution ledger.

No factor batch, parameter grid, portfolio grid, walk-forward run, final-holdout read, promotion, or paper signal is authorized by this source audit.

## What This Means For Profitability

This repair removes a real data bottleneck; it does not prove a profitable strategy. The next prescreen must still demonstrate:

- statistically credible out-of-sample directional evidence;
- positive spread after at least 10 bps round-trip stress;
- sufficient ETF liquidity and participation capacity;
- low duplication with the closed price, liquidity, volatility, and dynamic-peer families;
- stability across time without accessing the sealed 2026 holdout.

## Safety

Research-to-paper only. No broker connection, account read, order placement, automatic live trading, or claim of realized profit.
