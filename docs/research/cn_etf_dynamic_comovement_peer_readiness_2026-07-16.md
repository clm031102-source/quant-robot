# CN ETF Dynamic Co-Movement Peer Readiness Audit

Date: 2026-07-16

Branch: `codex/factor-review-cn-etf-dynamic-comovement-20260716`

Primary market: `CN_ETF`

Decision: `ready_for_peer_source_preregistration`

## Executive Decision

The lagged dynamic co-movement source passed its frozen point-in-time readiness gates on the local 2020-01-02 through 2024-06-28 CN ETF history. The result permits exactly one later, source-locked peer-dislocation prescreen preregistration. It does not establish alpha, profitability, portfolio viability, or permission to generate factor values.

The scheduler therefore keeps this family at zero budget and keeps factor batches disabled. The next valid action is to write and separately review one compact preregistration. Forward returns, factor values, portfolio grids, walk-forward validation, paper signals, the 2026 final holdout, and all live boundaries remained untouched.

## Problems Corrected

1. Repaired the shared ETF lifecycle loader so legitimate symbols repeated across distinct dated authority snapshots use the latest row while older-only delisted ETFs remain available. Duplicates inside one snapshot, or duplicates without distinct dated authorities, still fail closed.
2. Replaced current-name, current-theme, and current official peer inference with quarterly peer sets built only from information available through the prior market session.
3. Removed the common ETF market component before peer selection, reducing the chance that broad beta alone defines every peer set.
4. Made selection deterministic: residual-correlation threshold 0.50, at most five peers, at least three peers, and asset identifier as the final tie-break.
5. Added interval validation for source dates, reversed intervals, duplicate directed edges, and overlapping validity intervals.
6. Added future-invariance tests proving that appending later bars cannot change already-issued mappings.
7. Added stability, retention, complete-churn, reciprocity, and scalar-nearest-neighbor duplicate gates.
8. Corrected the initial coverage implementation. A date now counts an asset only when the asset and at least three mapped peers remain eligible on that date; quarterly snapshot membership alone no longer inflates daily coverage.
9. Added a frozen, fail-closed command entrypoint that rejects threshold drift, holdout access, current-name input, factor generation, portfolio execution, and live boundaries.
10. Added a `preregistration_only` Quant PM startup mode. It permits `factor_review` to write the next frozen preregistration while factor batches remain disabled.

## Frozen Method

| Component | Frozen rule |
| --- | --- |
| Rebalance dates | First session of January, April, July, and October |
| Knowledge cutoff | Prior market session; always earlier than `valid_from` |
| Return window | 120 adjusted-close returns |
| Minimum asset returns | 100 |
| Market return | Cross-sectional median; minimum 30 assets |
| Residual model | OLS alpha and beta; minimum 80 paired observations |
| Peer similarity | Residual-return correlation; minimum 80 overlapping observations |
| Selection | Correlation at least 0.50; deterministic top five; minimum three peers |
| Eligibility history | 120 prior observations |
| Liquidity | Median ADV20 at least CNY 5 million |
| Data quality | Stale-rate at most 5%; absolute one-session return at most 20% |
| Lifecycle | Inside official list/delist interval |
| Coverage gate | At least 30 daily-usable mapped assets on at least 80% of all dates |

No forward label appears in peer construction. The source did not use current ETF names, the official 2026 peer snapshot, future returns, or factor values.

## Real Evidence

| Check | Result |
| --- | ---: |
| Historical rows | 1,119,490 |
| Historical assets | 1,781 |
| Lifecycle assets | 1,768 |
| Analysis sessions | 1,085 |
| Mapping rows | 20,301 |
| Mapped source assets | 681 |
| Peer assets | 651 |
| Usable mapping snapshots | 15 |
| Earliest usable mapping date | 2020-10-09 |
| Latest usable mapping date | 2024-04-01 |
| Qualifying dates | 904 / 1,085 |
| Qualifying-date coverage | 83.317972% |
| Daily eligibility intersection | Required and used |
| Daily-usable mapped assets | min 0, median 214, max 436 |
| Stability transitions | 14 |
| Minimum comparable assets | 92 |
| Minimum median Jaccard | 0.428571 |
| Minimum median retention | 0.600000 |
| Maximum complete churn | 0.071429 |
| Snapshot reciprocity | 0.588665 to 0.743390 |
| Selected median residual correlation | 0.844589 to 0.933796 |

Warm-up sessions remain in the 1,085-date denominator. Across active mapping dates, the snapshot population ranged from 115 to 440 assets; the daily eligibility intersection reduced the usable count whenever an asset or too many peers failed lifecycle, history, liquidity, stale-price, or extreme-return checks.

## Gate Results

| Gate | Threshold | Worst observed | Result |
| --- | ---: | ---: | --- |
| Qualifying-date coverage | at least 0.80 | 0.833180 | pass |
| Comparable assets per transition | at least 30 | 92 | pass |
| Median peer-set Jaccard | at least 0.25 | 0.428571 | pass |
| Median peer retention | at least 0.40 | 0.600000 | pass |
| Complete churn | at most 0.40 | 0.071429 | pass |
| Reciprocity | at least 0.30 | 0.588665 | pass |
| Duplicate evidence coverage | at least 0.80 | 0.928460 | pass |
| Scalar-reference edge overlap | below 0.50 | 0.301708 | pass |
| Leakage and interval integrity | zero violations | zero | pass |

Maximum edge overlap by frozen reference was 0.055249 for log ADV20, 0.267826 for market beta, 0.285714 for 60-session momentum, 0.301708 for 60-session residual volatility, and 0.248696 for five-session return. This clears the source-duplication gate but does not prove the future peer-dislocation signal will be economically distinct after labels are introduced.

## Reproducibility

Frozen config SHA-256: `a3eeda49ade9624c1e335d9adfc7a6cdd0803def723feda9ef28a99d1e9c6016`

Result JSON SHA-256: `4177895b7799c5074ab0b7a0102f9a1f3917d789817e5b2380497c08346fac44`

The real audit was run twice. All durable machine-artifact hashes were identical:

| Artifact | SHA-256 |
| --- | --- |
| `dynamic_peer_mapping.csv` | `52d7c0c80b32b164583bea52cc09e0fba7436051d236df6e1ab9343387f5fe63` |
| `snapshot_summary.csv` | `fc47e4c0d2d73f7019c51abfcd13299736602e1fe5ac6ef1cd84eff12268ba91` |
| `coverage_by_date.csv` | `59e3c3fa52ae1dc53f9b40d4826d925224f1ab0c6075dc0dfdfa3a387220035d` |
| `stability_by_transition.csv` | `d86b20374252b48a56d5963983541eb4ac5d4674cc3be5150bf8fe73ee4e361c` |
| `duplicate_overlap.csv` | `1483b0b677bf3b434e2fef5dac7a49b7592956e3dc72d365ee815117910c6a1a` |

Generated evidence remains under ignored path `data/reports/cn_etf_dynamic_comovement_peer_readiness_20260716/` and is not eligible for Git.

## Limitations And Residual Risk

- This is source readiness, not alpha evidence. The later peer-dislocation factor can still produce zero or negative out-of-sample IC and net return.
- The 83.32% coverage result exceeds the 80% gate by only 3.32 percentage points. Coverage is adequate, but the margin is modest.
- History ends on 2024-06-28. The missing 2024-H2 through 2025 period must be backfilled and audited before walk-forward validation; the 2026 holdout cannot be used to fill that gap.
- The available lifecycle snapshots are later authority captures. They are used only for identity and list/delist validity, never as historical peer assignments or predictive features.
- Official historical benchmark assignments, ETF holdings, daily share/size, and NAV histories remain unavailable. Those separate source families stay blocked.
- Dynamic peers are still price-derived. Passing beta, volatility, momentum, short-return, and liquidity topology checks reduces duplication risk but cannot eliminate hidden exposure overlap.
- The next preregistration must count this as one hypothesis family, freeze direction and horizons before labels are read, track every tested row, apply multiple-testing control, and require capacity/cost checks before any portfolio stage.
- Existing project maintainability debt remains: oversized legacy modules and sparse workflow-level integration tests. This branch adds focused regression coverage but does not justify unrelated broad refactoring.

## Scheduler Decision

`cn_etf_dynamic_comovement_peer_dislocation` is registered as exploratory with zero budget. Its source status is `ready_for_peer_source_preregistration`, `preregistration_required=true`, and `factor_batch_before_preregistration_allowed=false`. The scheduler remains intentionally blocked with 100% unallocated primary budget.

The only authorized next direction is `preregister_one_dynamic_peer_dislocation_prescreen`. A later review must reject any preregistration that changes the frozen peer source, expands into a parameter grid, reads the final holdout, or reopens closed standalone momentum, volatility, reversal, or broad-theme families.

## Completion Boundary

This audit closes the known dynamic-peer source-readiness defects and creates a reproducible path to one preregistered prescreen. It does not complete the overall project and does not support a profitability claim. The project remains research-to-paper only: no broker connection, account read, order placement, or automatic live trading.
