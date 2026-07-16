# CN ETF Peer Relative-Value Metadata Readiness

Date: 2026-07-16
Branch: `codex/factor-review-cn-etf-peer-relative-value-20260716`
Primary market: `CN_ETF`
Decision: `blocked` for factor generation; source repair only

## Executive Decision

The same-index or tightly defined same-theme relative-value family is not historically runnable on the current local data. The project now has an official benchmark-text snapshot for 1,611 ETFs and 675 benchmark identities, but the first defensible knowledge date is 2026-07-16. The 2020-01-02 through 2024-06-28 analysis window therefore has zero qualifying peer dates. Applying this snapshot to earlier dates would be lookahead.

No peer-relative factor, portfolio grid, walk-forward run, paper signal, or profitability claim is authorized. The family remains economically plausible but source-blocked, not statistically rejected.

## Reproducible Evidence

| Check | Result |
| --- | ---: |
| Historical bar rows | 1,119,490 |
| Historical ETF assets | 1,781 |
| Historical sessions | 1,085 |
| Analysis window | 2020-01-02 to 2024-06-28 |
| Fund-basic snapshots | 2 |
| Latest snapshot | 2026-07-16 |
| Official peer-mapping rows | 1,611 |
| Official benchmark identities | 675 |
| Current groups with at least two ETFs | 241 |
| Current ETFs in groups with at least two members | 1,177 |
| Earliest defensible mapping knowledge date | 2026-07-16 |
| Analysis dates with at least 30 mapped peer assets | 0 / 1,085 |
| Qualifying-date coverage | 0.0% |
| Historical ETF share/NAV rows | 0 |

Frozen config SHA-256: `5eee324a902a0c4bf9b228ae9f233d8f790c52a9d27037bb7a6a466819cac3fa`
Result JSON SHA-256: `8a23185f04648a1aeef48a273dcb16e4940a24100b953bd17c6e71f837b1afc1`

Generated evidence is stored under ignored path `data/reports/cn_etf_peer_relative_value_metadata_readiness_20260716/`.

## Problems Corrected

1. Added a fail-closed metadata gate for required fields, usable close history, approved mapping methods, knowledge dates, validity intervals, overlapping assignments, peer-group size, daily cross-section coverage, and sealed holdout boundaries.
2. Replaced the inappropriate 80% all-asset-date requirement with a factor-relevant gate: at least 30 qualifying peer assets on at least 80% of analysis dates.
3. Prohibited current-name keyword themes from clearing the peer gate. The latest heuristic map has 18 broad groups, only 53.17% historical asset coverage, median group size 67, and maximum group size 263; it is descriptive, not a tight peer taxonomy.
4. Preserved the official `fund_basic.benchmark` field that the adapter previously discarded. The live snapshot returned benchmark text for all 2,143 listed funds and all 1,611 classified ETFs.
5. Added normalized `etf_basic.index_code` support and a conservative snapshot-to-validity mapping builder. The live `etf_basic` call was denied by the current token, so this path is implemented and tested but not treated as available data.
6. Added exact official benchmark-text grouping as a fallback source. Unicode and whitespace are normalized, but no semantic name inference is performed.
7. Forced every new official assignment to become usable no earlier than its captured snapshot date. Listing dates are retained for description but never used to backfill knowledge.
8. Made Tushare permission denials non-retryable, avoiding repeated requests that cannot succeed.
9. Removed all primary budget from source-blocked flow-breadth, fund-structure, and peer-relative-value families. The scheduler is intentionally blocked with zero primary allocation.
10. Added `source_repair_only` startup mode for `data_pipeline` and `factor_review`. It permits metadata/data repair while keeping factor batches disabled.
11. Rejects empty `fund_basic` or `etf_basic` provider responses before any snapshot or consolidated mapping is written, preserving the last valid authority state.
12. Drops future-listing assignments whose next snapshot closes before `valid_from`, preventing impossible `valid_from > valid_to` intervals.

## Source Assessment

The official Tushare documentation confirms that `fund_basic` exposes a benchmark field, `etf_basic` exposes an ETF tracking `index_code`, and `etf_share_size` exposes daily share, size, NAV, and close data:

- [Tushare fund_basic](https://tushare.pro/document/1?doc_id=19)
- [Tushare etf_basic](https://tushare.pro/document/2?doc_id=385)
- [Tushare etf_share_size](https://tushare.pro/document/2?doc_id=408)

Local access differs by endpoint. `fund_basic` succeeded. `etf_basic` was denied by provider permissions, and the long-history root still has no `etf_share_size` or ETF holdings/basket dataset. API existence is therefore not counted as local readiness.

## Remaining Blockers

- No audited official ETF-to-benchmark history is known during 2020-2024.
- No historical daily ETF share, size, or NAV series is locally available.
- No point-in-time holdings or audited historical theme bridge exists for stock-flow aggregation.
- The long-history root has no rotation-membership pack or current sync pack; generic data readiness remains blocked.
- The analysis history ends on 2024-06-28. The 2026 final holdout remains sealed and cannot repair missing 2024-H2 through 2025 evidence.
- Current benchmark text can support forward accumulation from 2026-07-16, but it cannot justify historical backfill without dated official evidence.

## Project-Level Residual Debt

- The maintainability baseline still records 13 oversized source modules. This branch adds no regression, but the largest existing modules remain expensive to review and change safely.
- The test topology remains unit-heavy: 566 unit-test files, 2 integration-test files, and no end-to-end test layer.
- Integration coverage is therefore sparse around complete operator workflows even though the full unit/integration discovery suite passes.
- The office desktop's system `python` is 3.14.6, outside the project's declared `>=3.11,<3.14` range. Formal verification used the repository `.venv` on Python 3.12.13; future commands should use that interpreter explicitly.
- These are structural follow-up items, not authorization to mix broad refactoring into a source-readiness research branch.

## Verification

- Formal verification runtime: repository `.venv`, Python 3.12.13.
- Focused change-surface tests: 63 passed.
- Full repository test discovery: 2,260 passed in 693.747 seconds.
- Python compilation: passed for `src`, `scripts`, and `tests`.
- Project audit: passed; 2,784 files and 82 factor configs scanned, with no forbidden safety hits, syntax errors, invalid factor configs, unknown factor references, or unsupported factor sources.
- Maintainability audit: `baseline_passed_with_known_debt`; no baseline regressions.
- Quant PM startup gate: `ready` in `source_repair_only` mode; factor batches remain disabled.
- Git whitespace validation: passed; only expected Windows line-ending conversion warnings were emitted.

## Scheduler Decision

The prior allocation of 35% flow breadth, 35% fund structure, and 30% peer relative value has been released. Unallocated research budget is now 100%. This prevents missing-source families from appearing factor-ready and preserves the stop-losses on price rotation, liquidity capacity, and volatility regime.

The next direction is a separate readiness review for `cn_etf_dynamic_comovement_peer_dislocation`. It may derive peers only from lagged historical returns, must use information available by T-1, and must first prove that it is not a disguised retry of closed price-rotation, volatility, broad-theme, or short-horizon reversal families. No factor implementation is allowed until that review clears leakage, stability, coverage, and duplicate gates.

## Completion Boundary

This work completes the metadata-readiness audit and repairs the known collection/governance defects. It does not complete the overall research project and does not establish a profitable strategy. Research remains strictly research-to-paper: no broker connection, account read, order placement, or automatic live trading.
