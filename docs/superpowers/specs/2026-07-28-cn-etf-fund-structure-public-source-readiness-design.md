# CN ETF Fund-Structure Public-Source Readiness Design

Date: 2026-07-28

Machine: `office_desktop`

Task: `factor_review`

Branch: `codex/factor-review-cn-etf-fund-structure-source-20260728`

## Objective

Determine whether daily ETF shares, NAV, close, scale, and premium/discount inputs can be assembled for the 2020-01-02 through 2024-06-28 CN ETF research window without look-ahead and with enough cross-sectional coverage to justify one later, separately preregistered fund-structure prescreen.

This stage is source collection and readiness only. It must not calculate forward returns, IC, portfolio returns, walk-forward performance, paper signals, or profitability.

## Evidence That Forces A Source Rotation

The repository's Tushare ingestion path already supports `etf_share_size`, but the live one-session probe on 2026-07-28 was rejected as a non-retryable provider permission failure. Repeating or expanding that request cannot repair the missing entitlement.

The local long-history ETF root contains no processed share/NAV dataset. Applying a current snapshot to 2020-2024 would be look-ahead and remains prohibited.

## Alternatives Considered

### Upgrade the Tushare entitlement

This is the cleanest operational path because the canonical adapter and storage contract already exist. It is not immediately executable with the current token, so it is retained as the fastest user-supplied acceleration option rather than the active path.

### Stop the family as externally blocked

This is safe but premature. Public exchange endpoints returned historical share records in live probes, so the project has a defensible repair path that should be audited before releasing the family.

### Public official share history plus public NAV history

Selected. Shanghai Stock Exchange and Shenzhen Stock Exchange endpoints provide dated ETF share history. Eastmoney's fund detail payload provides dated historical unit-NAV observations in one response per fund and avoids the broken 20-row pagination wrapper. Existing Tushare `fund_daily` bars remain the close and liquidity authority.

Share data is exchange-official. NAV data is a public secondary-source copy and must be labelled as such; it cannot be promoted to primary authority without coverage and value-consistency checks.

## Frozen Data Boundary

- Primary market: `CN_ETF`.
- Existing bar authority: `data/processed/tushare_etf_wide_history_2023_2026`.
- Analysis start: 2020-01-02.
- Analysis end: 2024-06-28.
- Final holdout start: 2026-01-01.
- 2026 rows must not be read or written into the readiness dataset.
- Fund codes are taken from bar-authority symbols observed inside the analysis window.

## Public Source Contract

### Shanghai shares

- Endpoint family: SSE common query, SQL id `COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L`.
- One request per observed market session.
- `STAT_DATE` is the requested session.
- `TOT_VOL` is converted from ten-thousand shares to shares.
- Only six-digit fund codes that join to the analysis bar authority are retained.

### Shenzhen shares

- Endpoint family: SZSE `ShowReport`, catalog `scsj_fund_jjgm`, tab `tab1`, category `ETF`.
- Requests are split into windows no longer than six calendar months.
- The returned workbook's date, fund code, and fund scale-in-shares fields are normalized.
- TLS and transient HTTP failures use bounded retries; schema or content errors fail closed.

### Historical NAV

- Endpoint family: Eastmoney `pingzhongdata/<fund-code>.js`.
- Only the `Data_netWorthTrend` JSON assignment is parsed.
- `x` is converted from Unix milliseconds to an Asia/Shanghai calendar date.
- `y` is normalized as unit NAV.
- Only observations inside the frozen analysis window are retained.
- A missing or malformed fund payload records a per-symbol failure; it never invents NAV.

## Acquisition And Resume Policy

- Output root: `data/processed/cn_etf_fund_structure_public_2020_2024`.
- Generated data and request manifests stay outside Git.
- Every request records source, parameters, retrieval status, row count, response SHA-256 when available, and a bounded error category.
- Completed share dates/chunks and NAV symbols are resumable.
- Raw payloads need not be retained when they are large; normalized rows plus response hashes and request metadata are the evidence contract.
- Concurrency is bounded and provider-specific. Retrying permission, schema, or empty-authority failures is prohibited.

## Point-In-Time Contract

All dated share and NAV inputs are treated as end-of-session observations and become factor-eligible no earlier than the next observed market session.

Persisted normalized rows contain:

- `date`
- `known_from`
- `asset_id`
- `symbol`
- `exchange`
- `total_share`
- `nav`
- `close`
- `total_size`
- `nav_premium_discount`
- `share_source`
- `nav_source`
- `close_source`

`known_from` must be strictly later than `date`. `total_size` is `total_share * nav`. Premium/discount is `close / nav - 1`. Derived values are null unless both inputs are finite and positive.

## Frozen Readiness Gates

The source is ready for later preregistration only when all gates pass:

1. No duplicate `asset_id`/`date` rows after source-specific normalization.
2. Every retained row is inside the frozen analysis window and every `known_from` is later than `date`.
3. Combined share coverage has at least 30 bar-authority assets on at least 80% of analysis sessions.
4. Each exchange has share observations on at least 75% of sessions on which that exchange has at least 30 eligible bar assets.
5. On qualifying combined-share sessions, the median share-covered fraction of bar-authority assets is at least 50%.
6. At least 70% of share/bar intersections have positive NAV and therefore usable scale and premium/discount inputs.
7. At least 95% of retained share values and at least 95% of retained NAV values are finite and positive.
8. Close values come only from the frozen bar authority and join without duplicate asset-session rows.
9. No 2026 holdout row, factor label, forward return, or performance result is read.

Failure produces exact source blockers and releases no factor-batch permission.

## Result States

### `ready_for_fund_structure_preregistration`

Authorizes only a later design and hash-bound preregistration for one compact fund-structure prescreen. It does not authorize factor generation in this task.

### `blocked`

Records exact provider, coverage, schema, or point-in-time blockers. The scheduler keeps the family at zero budget and rotates to the next orthogonal source-readiness review.

## Required Artifacts

- Frozen JSON config.
- Retry-safe public-source adapter.
- Resumable ingestion and normalization operation.
- Pure readiness audit and strict CLI.
- Unit tests for parsing, normalization, resume, leakage, coverage, and disabled execution boundaries.
- Ignored normalized data, manifests, JSON/Markdown summaries, and coverage CSVs.
- Durable research report, scheduler decision, and research-index update.

## Safety

Research-to-paper only. Factor generation, portfolio grids, walk-forward runs, final-holdout reads, paper signals, broker connections, account reads, order placement, and automatic live trading remain disabled.
