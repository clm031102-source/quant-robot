# Desktop Validation Evidence Closure Design

## Context

The residual-regime desktop validation profile is documented as the stable CN stock validation entrypoint, but the current executable chain is no longer reproducible after the repository's strict data-loader hardening:

- the profile points at `data/processed`, which is not an unambiguous processed-bar store;
- the walk-forward config points at a moneyflow directory that does not exist;
- the quality audit has no explicit trading calendar;
- a strict per-asset calendar audit treats ordinary CN stock suspensions as missing data;
- the generic factor-batch readiness packet is designed for active factor discovery, not frozen historical validation;
- the profile scans the whole `data` tree even though its authoritative inputs are already declared by tracked segment configs.

The repair must make the validation executable and reproducible without reopening a rejected factor family, weakening promotion controls, touching the 2026 final holdout, or adding any live-trading capability.

## Chosen Approach

Build a validation-specific evidence chain around the existing walk-forward engine.

1. Load CN bars only through the tracked adjusted-ratio-clean authority config.
2. Load moneyflow only through its tracked authority config.
3. Materialize a provider-backed CN trading calendar from synchronized Tushare SSE and SZSE sessions, with an artifact hash and provenance manifest.
4. Distinguish whole-market session loss from unexplained per-asset gaps. Whole-market loss remains a hard blocker; per-asset gaps become `review_required` until suspension evidence explains them.
5. Generate a factor-validation readiness packet that binds the current-day startup gate, walk-forward config hash, exact factor names, authority data configs, data manifest, calendar manifest, final-holdout boundary, and research-only safety boundary.
6. Let generic CN walk-forward runs accept either the existing factor-batch gate or the new validation gate, never an implicit bypass.
7. Rewire `desktop-validation` to run only scoped, relevant checks and to continue through a review-required stock gap audit while keeping promotion blocked.

This is preferred over restoring recursive discovery because recursive loading would reintroduce ambiguous data. It is preferred over forcing zero per-stock gaps because suspended stocks do not produce ordinary daily bars. It is preferred over manufacturing a factor-batch readiness packet because the active-source queue intentionally excludes this already-rejected historical family.

## Trading Calendar Contract

The calendar artifact covers 2015-01-01 through 2025-12-31 and is independent of observed bars.

- Provider: Tushare.
- Endpoint: `trade_cal`.
- Required source exchanges: `SSE` and `SZSE`.
- Required invariant: both exchanges return the same non-empty open-session set.
- Market mapping: the synchronized set is the CN market calendar, including BSE instruments because BSE follows the same national trading sessions while Tushare's `BSE` calendar query is empty.
- Artifact columns: `market`, `date`, `is_open`, `source`.
- Manifest evidence: requested and effective ranges, exchange row counts, exchange date fingerprints, synchronized-session fingerprint, artifact SHA-256, row count, provider/endpoint, generation timestamp, and research-only safety text.
- Validation: reject missing files, duplicate dates, out-of-range dates, altered artifacts, wrong provider/endpoint, missing exchanges, empty calendars, or manifest/artifact mismatches.

Generated calendar data stays under ignored `data/processed`; code, tests, and documentation remain tracked.

## Authority Data Contract

Add an explicit `authority-bars` walk-forward source. It accepts only a file-backed authority config and uses `load_authority_processed_bars_from_config`; it never falls back to recursive discovery.

The CN stock data-manifest command gains a distinct moneyflow root and authority-config support. The packet records both bar and moneyflow roots and fingerprints. Validation compares the expected authority paths and verifies referenced dataset inventories before the walk-forward starts.

The residual-regime walk-forward config is repaired to point at `configs/cn_stock_authority_moneyflow_inputs_2015_2025.json`. The authority bars config remains `configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json`.

## Stock Gap-Audit Semantics

The default policy remains strict for ETFs and other continuous instruments. A new explicit asset-gap policy supports CN stocks:

- `block`: any per-asset missing session blocks the audit (existing behavior).
- `review`: whole-market missing sessions still block; per-asset gaps produce `review_required`, diagnostics, and a promotion blocker until suspension/tradeability evidence is supplied.

The CLI exits successfully for `review_required` only when `--allow-review-required` is present. The desktop profile uses this explicit acknowledgement. The promotion gate continues to see `gap_audit_cleared=false`, so review-required data cannot be promoted.

## Factor Validation Readiness Contract

The new packet is separate from factor-batch discovery readiness. It validates and records:

- a cleared same-day CN stock startup gate for `factor_validation`;
- a branch using `codex/factor-validation-cn-stock-`;
- `authority-bars` as the data source;
- the exact walk-forward config path, SHA-256, markets, factors, and end date;
- an authority bar config capped at 2025-12-31;
- the moneyflow authority config referenced by the walk-forward config;
- a usable same-day CN data manifest whose source paths and fingerprints match;
- a valid provider calendar covering the complete authority window;
- no final-holdout access and no promotion/live permission.

The walk-forward validator rechecks the packet against its effective config and source path. A stale or cross-profile packet fails closed.

## Desktop Profile Order

The repaired profile runs:

1. tests, compile checks, project audit, readiness check, and provider status;
2. local calendar artifact validation;
3. authority CN data-manifest generation;
4. authority-bar data-quality audit with calendar provenance and review-only asset gaps;
5. factor-validation readiness generation;
6. authority-backed walk-forward validation;
7. regime coverage, promotion report, and lightweight summary.

The unscoped whole-`data` catalog scan is removed from this profile because it is unrelated to the declared authority inputs and has already exceeded the operational timeout. General catalog tooling remains available elsewhere.

## Scientific Boundary

This work repairs validation infrastructure; it does not revive the residual moneyflow family as a new alpha direction. A complete rejection set remains valid evidence. Any accepted row is still blocked from promotion while the stock gap audit is review-required or any other promotion evidence is missing.

The 2026 final holdout remains sealed. No broker connection, account read, order placement, or live-trading path is introduced.

## Acceptance Criteria

1. Calendar unit tests prove synchronized exchange validation and artifact tamper detection.
2. Gap-audit tests prove strict defaults, stock review semantics, and hard blocking of whole-market loss.
3. Walk-forward tests prove authority loading and prove that CN validation cannot run without a matching validation or factor-batch readiness packet.
4. Data-manifest tests prove separate authority bar/moneyflow roots and referenced-data fingerprint validation.
5. Desktop profile tests assert the exact authority paths, calendar evidence, and validation packet chain.
6. The real 2015-2025 calendar artifact validates locally.
7. The full desktop validation chain either completes or stops on a quantified external evidence blocker; no stale output is reported as current.
8. Focused tests, full tests, compile checks, project audit, and diff checks pass before commit.
9. Generated data/reports remain untracked, and no push is performed from the office desktop.
