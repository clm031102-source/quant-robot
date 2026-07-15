# CN Stock PIT Session Integrity Design

## Context

The 2015-2025 CN stock authority bars contain 8,450,716 rows across 4,726 assets and all 2,674 expected market sessions. The existing asset-level gap audit reports 337,904 sessions between each asset's first and last observed bars.

The full evidence reconciliation performed on 2026-07-16 found:

- 174,865 gaps matched the existing official Tushare `suspend_d` daily evidence.
- 154,735 gaps occurred before the official `stock_basic.list_date`, all on XBEI assets.
- 7,936 active-window gaps remained unexplained across 37 assets.
- 368 gaps belonged to three assets absent from the current `stock_basic` snapshot.
- 48,990 observed XBEI bars occurred before the official listing date.
- 3,006 adjusted-close transitions exceeded 50%; 765 touched out-of-lifecycle bars and 1,941 coincided with a large adjusted-ratio change.

The current audit therefore mixes legitimate suspension gaps, exchange-transition history, and source defects. A single `review_required` count cannot safely support future research.

## Goals

1. Classify every asset-session gap with explicit official evidence.
2. Separate sessions outside the official listed lifecycle from expected listed sessions.
3. Add legacy Tushare suspension intervals only for assets still unresolved after daily suspension evidence.
4. Quarantine out-of-lifecycle bars and adjustment discontinuities in a new authority view without rewriting source data.
5. Produce a structured extreme-return audit that distinguishes source anomalies from plausible post-suspension repricing.
6. Fail closed when lifecycle metadata or event evidence is incomplete.

## Non-Goals

- Do not fill missing bars with synthetic prices or zero-volume observations.
- Do not infer suspension solely from missing prices.
- Do not retune or rerun the rejected residual-moneyflow family.
- Do not use the 2026 holdout or connect to a broker, account, order, or live-trading boundary.
- Do not treat retrospective lifecycle or legacy suspension metadata as an alpha feature.

## Considered Approaches

### 1. Refresh all daily bars

Refreshing the whole market would be expensive and would still leave legitimate suspensions indistinguishable from provider gaps. It also needlessly consumes provider quota.

### 2. Infer missing sessions from neighboring prices

This is unsafe. Long gaps can represent suspension, delisting, exchange migration, or provider loss. Price-only inference cannot establish the cause.

### 3. Evidence overlay with targeted repair

This is the selected approach. It preserves raw data, applies official lifecycle and suspension evidence, fetches legacy intervals only for unresolved assets, and reserves bar refresh for the final unexplained residue.

## Architecture

### Asset-session audit core

Add a pure module that accepts:

- authority bars;
- explicit trading sessions;
- all-status `stock_basic` metadata;
- `suspend_d` daily evidence;
- optional legacy `suspend` intervals.

For every asset, the raw diagnostic interval remains first observed date through last observed date. The official expected interval is clipped to `list_date` and `delist_date`. Every missing raw session receives exactly one classification:

- `before_official_list_date`;
- `after_official_delist_date`;
- `official_daily_suspension`;
- `official_legacy_suspension`;
- `missing_lifecycle_metadata`;
- `unresolved_active_session`.

Official suspension evidence takes precedence inside the listed lifecycle. Lifecycle dates remove sessions from the expected listed universe; they never create bars. Missing metadata and unresolved active sessions remain blockers.

The audit also reports observed bars outside the official lifecycle. XBEI pre-listing history is labelled as exchange-transition contamination, not silently discarded from the audit.

### Targeted legacy suspension ingestion

Extend the Tushare adapter with a symbol-scoped legacy `suspend` call. A dedicated ingestion command reads the unresolved-asset output and fetches only those symbols. It normalizes `19000101` resume dates to open-ended intervals, records source and ingestion time, and marks the dataset as data-quality evidence only.

The command must validate the requested asset/symbol mapping, reject duplicate intervals, and never broaden itself to an unbounded all-market request.

### Lifecycle-clean authority view

Extend authority-bar configuration with optional lifecycle controls:

- `stock_basic_root`;
- `enforce_official_lifecycle`;
- `exclude_assets_without_lifecycle_metadata`.

Create a new config rather than mutating the historical clean config. The new view excludes pre-list, post-delist, and unknown-lifecycle assets at read time. The source parquet files remain unchanged, preserving prior evidence reproducibility.

The adjustment-ratio quarantine threshold in the new view is 1.5. This is a price-integrity invariant chosen before any factor result is read: an adjustment-ratio discontinuity large enough to help create a greater-than-50% adjusted return cannot enter future research.

### Extreme-return audit

Add a separate pure audit over lifecycle-clean bars. For each absolute adjusted return above 50%, record previous/current dates and prices, raw return, adjusted-ratio change, elapsed days, lifecycle state, and suspension evidence.

Classifications are:

- `adjustment_ratio_discontinuity`;
- `outside_official_lifecycle`;
- `official_post_suspension_repricing`;
- `raw_price_discontinuity`;
- `combined_price_adjustment_move`.

Adjustment and out-of-lifecycle classes are hard data blockers. Official post-suspension repricing is retained as review evidence because a real reopened price can move beyond normal daily limits. Remaining unexplained transitions are blockers.

## Outputs

The session audit writes:

- `cn_stock_asset_session_integrity_audit.json` and `.md`;
- `asset_session_gap_classifications.csv`;
- `unresolved_asset_sessions.csv`;
- `unresolved_assets.csv`;
- `observed_outside_lifecycle.csv`;
- `coverage_by_asset.csv`.

The price audit writes:

- `cn_stock_price_integrity_audit.json` and `.md`;
- `extreme_return_rows.csv`;
- `price_integrity_blockers.csv`.

Generated data and reports remain under `data/` and stay out of Git. Code, configs, tests, and lightweight research summaries are committed.

## Decision Semantics

The session audit is:

- `blocked` when evidence coverage is absent, lifecycle metadata is missing for an included asset, observed bars violate the lifecycle, or active sessions remain unresolved;
- `review_required` when every gap is explained but retrospective data-quality evidence remains;
- `cleared` only when all expected listed sessions are either observed or officially suspended and no lifecycle contamination remains.

The price audit is:

- `blocked` for adjustment, lifecycle, or unexplained raw-price anomalies;
- `review_required` when only official post-suspension repricing remains;
- `cleared` when no extreme transitions remain.

Future CN stock research must use the new authority config and must not claim promotion while either audit is blocked. CN stock moneyflow remains auxiliary-only; the primary research market remains CN_ETF.

## Verification

Unit tests cover classification precedence, open-ended legacy intervals, lifecycle filtering, duplicate evidence rejection, adjustment discontinuities, and official resumption moves. CLI tests cover local artifact loading, deterministic outputs, blocked exit behavior, and research-only safety fields.

The end-to-end check runs both audits on the 2015-2025 authority data, performs the targeted legacy suspension fetch, reruns the audits, and records the exact unresolved residue. The existing full project test suite and project audit must still pass.
