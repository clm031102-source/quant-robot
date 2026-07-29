# CN ETF Tushare NAV Source Readiness Design

Date: 2026-07-29

Machine: `office_desktop`

Task: `factor_review`

Branch: `codex/factor-review-cn-etf-current-access-20260728`

## Objective

Determine whether the locally available Tushare `fund_nav` entitlement can
replace or independently corroborate the secondary public NAV copy for the
2020-01-02 through 2024-06-28 CN ETF research window.

This stage is source collection and readiness only. It must not calculate a
factor, read a forward return, run a portfolio, inspect the 2026 final holdout,
or claim that a strategy is profitable.

## Programme Decomposition

The 24-hour programme is split into separate fail-closed subprojects:

1. This source-readiness audit collects announcement-dated Tushare NAV and
   compares it with the frozen public fund-structure source.
2. A later preregistration may freeze exactly one delayed NAV-premium
   innovation candidate only if this source audit passes.
3. A later one-use prescreen may read labels only after the preregistration
   creates a hash-bound authorization.
4. Walk-forward, paper observation, and small-capital review remain separate
   later gates and are available only if the single prescreen passes.

Failure in any subproject closes the route without sign changes, window
changes, threshold relaxation, or reuse of the sealed final holdout.

## Evidence And Alternatives

### Tushare announcement-dated NAV

Selected. A live bounded probe returned 1,091 `fund_nav` rows for
`510300.SH` from 2020-01-02 through 2024-06-28, with both `nav_date` and
`ann_date`. The endpoint is available with the current entitlement and supplies
the publication date missing from the public Eastmoney history.

### Continue with only the public NAV copy

The existing source has 642,285 positive NAV rows and 99.479590% NAV
intersection coverage. It remains useful as comparison evidence, but its
synthetic next-session availability rule is weaker than an explicit
announcement date.

### Wait for historical PCF or ETF benchmark mapping

Historical PCF and official ETF mapping remain higher-value future sources, but
their 8,000-point entitlement is unavailable. Waiting would not improve the
current-access route during the requested 24-hour window.

### Fund dividend events

Rejected as the primary route. A deterministic 40-ETF cross-exchange probe
found only four funds, 34 positive-cash records, and 17 announcement dates in
the analysis window. That evidence is too sparse for the intended daily
cross-sectional programme.

## Frozen Data Boundary

- Primary market: `CN_ETF`.
- Analysis start: 2020-01-02.
- Analysis end: 2024-06-28.
- Final holdout start: 2026-01-01.
- Target universe:
  `data/processed/cn_etf_pcf_target_universe_2020_2024/target_universe.csv`.
- Existing comparison source:
  `data/processed/cn_etf_fund_structure_public_2020_2024`.
- Existing close authority:
  `data/processed/tushare_etf_wide_history_2023_2026`.
- Official calendar authority: the fingerprinted Tushare SSE/SZSE calendar
  already required by the Quant PM gate.
- Tushare requests must set an end date of 2024-06-28 and must discard any
  provider row outside the frozen window before persistence.

The target universe includes delisted funds. Current listing status must never
be used to remove a historical fund.

## Acquisition Contract

### Provider request

- Endpoint: `fund_nav`.
- One request per target-universe fund code.
- Required fields: `ts_code`, `ann_date`, `nav_date`, `unit_nav`,
  `accum_nav`, `accum_div`, `net_asset`, `total_netasset`, `adj_nav`, and
  `update_flag`.
- Requests use bounded retry only for transient provider failures.
- Permission, token, schema, and deterministic empty-result states are
  non-retryable.
- A resumable manifest records the request identity, status, row count,
  response-frame SHA-256, bounded error category, and completion timestamp.

### Canonical row

Each retained row contains:

- `nav_date`
- `ann_date`
- `known_from`
- `asset_id`
- `symbol`
- `exchange`
- `unit_nav`
- `accum_nav`
- `total_netasset`
- `update_flag`
- `source`

`known_from` is the first official CN market session strictly after both
`nav_date` and `ann_date`. A missing or unparseable announcement date does not
fall back to `nav_date`; it remains unusable and is counted by the readiness
gate.

Duplicate provider revisions for the same fund and NAV date are resolved only
when one row has a strictly later announcement date or a strictly higher
numeric `update_flag`. The selected revision retains its actual announcement
date. Ties with conflicting NAV values fail closed.

### Persistence

- Output root: `data/processed/cn_etf_tushare_nav_2020_2024`.
- Generated provider rows, manifests, and reports remain outside Git.
- Canonical data is partitioned by NAV year.
- Writes are atomic and resumable.
- Rerunning a completed request must not change canonical hashes unless the
  provider response itself changed; a changed response is recorded as a
  revision requiring re-audit.

## Comparison Contract

The existing public canonical source supplies comparison NAV for matching
`asset_id`/`nav_date` keys. The audit calculates:

- row and asset intersection coverage;
- absolute and relative NAV differences;
- agreement within 10 basis points;
- severe disagreement above 5%;
- announcement lag in calendar days and official market sessions;
- per-date usable cross-sectional breadth.

Comparison evidence does not silently overwrite either source. Tushare becomes
the candidate NAV authority only if every frozen readiness gate passes.

## Frozen Readiness Gates

The source is `ready_for_delayed_nav_premium_preregistration` only when:

1. Every target request has a terminal manifest state and there are no
   unresolved transient or provider errors.
2. Canonical `asset_id`/`nav_date` keys are unique.
3. Every retained NAV date is inside the frozen analysis window and there are
   zero 2026 rows.
4. At least 99% of retained rows have a valid `ann_date` on or after
   `nav_date`.
5. Every usable `known_from` is strictly after both `ann_date` and `nav_date`
   on the official calendar.
6. At least 99.9% of retained `unit_nav` values are finite and positive.
7. At least 90% of public-source NAV keys intersect the Tushare canonical
   source, and at least 90% of public-source NAV assets have one or more
   matched rows.
8. At least 99% of matched keys agree within 10 basis points, and no more than
   0.1% disagree by more than 5%.
9. At least 30 usable Tushare NAV assets are present on at least 80% of the
   official analysis sessions.
10. No factor, label, forward return, portfolio result, walk-forward result,
    paper signal, broker state, account state, or order state is read.

All ratios use explicit denominators in the result packet. Empty denominators
fail closed.

## Result States

### `ready_for_delayed_nav_premium_preregistration`

Authorizes only a separate design and hash-bound preregistration for one
candidate in a newly governed NAV-premium relative-value family. It does not
reopen the rejected fund-share crowding family and does not authorize a broad
share-size factor grid.

### `blocked`

Records exact permission, request, schema, announcement-timing, coverage,
agreement, breadth, duplicate, or holdout blockers. No factor generation or
label read is authorized.

## Planned Candidate Boundary

If the source passes, the next design will freeze one candidate:
`etf_delayed_nav_premium_innovation_reversal_60`.

The candidate will compare each ETF's announcement-lagged premium with its own
prior 60 usable observations, exclude the current observation from the robust
median and MAD baseline, remove frozen price, volatility, liquidity, scale,
and venue exposures, and predict reversal. Horizon 1 will be primary and
horizon 5 diagnostic only. This description reserves the research direction;
the exact formula and authorization must be frozen in the later
preregistration before any label is read.

## Operator Economics Already Supplied

The later cost and small-capital gates will use:

- capital stress range: CNY 1,000 to CNY 3,000;
- nominal commission: 0.5 basis points per side;
- expected slippage: 10 basis points per side;
- no-minimum-commission round trip: 21 basis points;
- conservative CNY 5 minimum-commission round-trip stress: approximately
  53.33 basis points at CNY 3,000 and 120 basis points at CNY 1,000;
- maximum single position for paper review: CNY 1,000;
- maximum paper daily loss: CNY 60;
- paper drawdown gate: 8%;
- user absolute drawdown veto: 40%;
- maximum holding period: 252 market sessions;
- maximum one-way participation: 1% of ADV.

The minimum-commission assumption remains a stress case until the future broker
confirms whether the CNY 5 minimum is waived.

## Required Artifacts

- Tushare adapter support for announcement-dated fund NAV.
- Resumable target-universe acquisition.
- Pure canonicalization and source-comparison operation.
- Strict source-readiness CLI and frozen JSON config.
- Unit tests for revisions, timing, duplicates, coverage, agreement, resume,
  forbidden boundaries, and deterministic hashes.
- Ignored canonical data, request manifest, coverage table, comparison table,
  and JSON/Markdown result.
- Durable research summary, scheduler decision, and current-index update after
  the real run.

## Safety

Research-to-paper only. Broker connection, account reads, order placement,
automatic execution, and live trading remain disabled. The existing paper and
manual-handoff infrastructure may be used only after a candidate passes every
research and paper gate.
