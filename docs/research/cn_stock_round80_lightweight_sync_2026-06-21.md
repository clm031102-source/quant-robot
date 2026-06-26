# CN Stock Round80 Lightweight Sync Boundary - 2026-06-21

## Purpose

Round80 is the ten-round governance boundary after the Round71-79 CN stock validation block. Its job is not to mine another factor. Its job is to package the useful code, configs, tests, and lightweight research summaries so the GitHub branch can be safely synchronized before rotating to the next factor family.

Scope stays CN A-share stock cross-sectional factor research. This is not CN ETF rotation and not live trading.

## Packaged Work

The sync package contains:

- public risk-filter bridge overlay audits from Round71-75;
- public RSRS pre-registration, long-cycle grid, translation audit, and costed bottom-exclusion walk-forward from Round76-79;
- the Round71-79 consolidated work report;
- reusable research tooling for cash overlays, beta exposure, beta-hedged spread audit, RSRS factors, and bottom-exclusion walk-forward validation;
- tests covering the new reusable tools and startup-gate expectations.

The sync package intentionally excludes:

- `data/raw/`;
- `data/processed/`;
- `data/reports/`;
- large Parquet/CSV outputs;
- logs;
- tokens, broker credentials, account data, order data, or live-trading secrets.

## Evidence Summary

Main research conclusion from the packaged block:

- Promotable profitable factors: 0.
- Paper-ready factors: 0.
- Immediate RSRS continuation candidates: 0.
- Public RSRS factor names registered: 4.
- Unique factor names directly evaluated in Round71-79: 7.
- Direct case rows reviewed: at least 38.
- Round79 rolling walk-forward folds: 7.

Most important bright data from Round71-79:

- `rsrs_reversal_18_60` industry-neutral RankIC: 0.0253, t-stat 24.00.
- `rsrs_reversal_18_60` bottom-exclusion diagnostic overlay t-stat: 5.39.
- Round79 costed walk-forward accepted folds: 0/7.
- Round79 mean test overlap-adjusted Sharpe: 0.0766.
- Round79 capacity-limited trades: 0.
- Round74 fixed a beta-hedged spread short-leg cost-sign bug that would otherwise have produced false positive spread evidence.

## Sync Audit Before Execution

`python scripts\sync_project.py --machine office_desktop --task factor_validation` was run before this report was added.

Result:

- Blockers: none.
- Branch discovery errors: none.
- Current branch: `codex/factor-validation-cn-stock-long-cycle-20260618`.
- Upstream sync: `0 0`.
- Blocked paths: none.
- Ignored paths: none.
- Syncable paths: configs, docs, scripts, source code, and tests only.

The audit noted one pending remote ETF research branch:

- `origin/codex/factor-batch-cn-etf-20260617`

That branch is not part of this CN stock factor-validation sync and does not block this task branch.

## Governance Decision

Round80 should commit and push the syncable lightweight package if execute-mode validation passes.

After the sync, the next mining direction is:

`round81_public_supertrend_exclusion_preregistration`

The next block must start with pre-registered SuperTrend/ATR-style hypotheses and signal-direction diagnostics before any wide portfolio grid. RSRS is hibernated as a promotion path after the zero-accepted-fold Round79 result.
