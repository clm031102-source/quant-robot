# CN Stock Session And Price Integrity Remediation Audit

Audit date: 2026-07-16

Machine: `office_desktop`

Task: `data_pipeline`

Branch: `codex/tushare-data-pipeline`

Parent evidence commit: `e44e591`

Scope: the Priority 0 CN stock authority-data findings from the desktop validation evidence closure, plus the adjacent experiment-cache and daily-factor computation debt that could be fixed without changing research outcomes.

## Executive Verdict

The scoped remediation is complete. The authority view now fails closed on official listing lifecycles, missing metadata, adjustment-ratio discontinuities, and explicit price-integrity quarantine. Every raw asset-session gap in the final view is explained by official daily or historical suspension evidence. The final price audit has no blocking rows. The schema-v5 data manifest binds both integrity packets by path and SHA-256 and has no blockers.

The final status is intentionally `review_required`, not `cleared`. This is caused by retrospective historical suspension evidence and 63 economically plausible but still reviewable extreme-return events. The status was not weakened to obtain a green result.

This work does not revive the rejected direct CN stock residual-moneyflow family. That family remains closed, CN stock moneyflow remains `auxiliary_only`, and 2026 remains sealed as the final holdout. The project remains research-to-paper only.

## Completion Assessment

Percentages apply only to the named gate. They are not profitability probabilities.

| Dimension | Completion | Verdict |
| --- | ---: | --- |
| This remediation task | 100% | Session classification, historical evidence, lifecycle cleaning, price root-cause audit, quarantine, manifest binding, tests, and documentation are complete |
| CN stock authority hard-blocker closure | 100% | Zero unresolved sessions, zero lifecycle contamination, zero missing lifecycle assets, and zero blocking price rows in the final view |
| CN stock authority review closure | 85% | All rows are classified, but retrospective legacy suspensions and 63 review-class price events remain explicitly acknowledged |
| Reproducible research platform | 92% | Full suite and project audit pass; dependency fingerprinting and daily factor pruning are improved; oversized-module and test-topology debt remains |
| Frozen residual-moneyflow evaluation | 100% evaluated | 96 of 96 candidates were rejected; the family must not be retuned |
| Frozen residual-moneyflow alpha readiness | 0% | No candidate reached paper observation or promotion |
| Live execution | 0% and out of scope | Broker, account, order, and automatic-live paths remain prohibited |

Overall stage: `pre-alpha / research-to-paper`. The repository is feasible for further preregistered CN ETF research, but it is not a completed or profitable trading product.

## Initial Findings

The original adjusted authority view contained:

- 8,450,716 bar rows across 4,726 assets and 2,674 market sessions.
- 337,904 raw asset-session gaps across 2,471 assets.
- 174,865 gaps covered by official daily suspension rows.
- 154,735 gaps before the official list date, all associated with historical BSE code/lifecycle transitions.
- 7,936 active-period gaps requiring the historical Tushare `suspend` endpoint.
- 368 gaps across three assets without official lifecycle metadata.
- 48,990 observed rows across 178 assets outside the official lifecycle.
- 3,006 adjusted-return transitions above 50% before lifecycle and adjustment-basis remediation.

The three assets without lifecycle metadata were `CN_XSHE_000022`, `CN_XSHE_000043`, and `CN_XSHE_300114`. They are now excluded fail-closed rather than assigned synthetic dates.

## Remediations

### Asset-Session Classification

Added a deterministic classification layer and audit packet covering:

- `before_official_list_date`
- `after_official_delist_date`
- `official_daily_suspension`
- `official_legacy_suspension`
- `missing_lifecycle_metadata`
- `unresolved_active_session`

The audit emits full row-level classifications, unresolved assets, lifecycle contamination, and per-asset coverage.

### Historical Suspension Evidence

Added a targeted Tushare legacy-suspension ingestion path. It:

- Queries only unresolved assets.
- Ignores provider rows outside the requested 2015-2025 window.
- Ignores same-day intraday suspension/resumption events that cannot explain a missing daily bar.
- Treats `19000101` as an open-ended resume marker.
- Rejects reversed intervals and duplicate evidence.
- Preserves the current asset identity while recording the historical provider symbol.

The final target set contained 44 assets. It produced 245 valid historical intervals for 41 assets. The provider returned 1,254 rows; 991 out-of-window rows and 18 intraday rows were ignored under explicit rules.

### BSE Historical Code Mapping

Current `920xxx.BJ` codes did not expose all historical suspension intervals. The ingest now applies the official BSE old/new code table and stores its SHA-256 provenance. Fifteen queried assets used mapped historical provider symbols.

Official source: <https://www.bse.cn/service/code_mapping.html>

Mapping artifact SHA-256: `95d43bba3b5ca2d6e5a2654755ea732ef52fa8d2c39fe667b5d4eab533a3b877`

This reduced unresolved active sessions from 113 to zero in the original authority view, then explained another 18 gaps exposed by lifecycle cleaning.

### Lifecycle-Clean Authority View

Added `configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json` without modifying the prior reproducibility config. The new view:

- Loads all official Tushare stock-basic lifecycle snapshots.
- Rejects duplicate asset identities and reversed lifecycle dates.
- Retains list and delist dates inclusively.
- Removes bars before listing and after delisting.
- Excludes assets without a valid official list date.
- Applies explicit price-integrity quarantine.

The final view contains 6,512,719 rows across 3,853 assets and all 2,674 market sessions.

### Adjustment-Basis Repair

The price audit identified 163 apparent mixed price/adjustment moves concentrated on four provider transition dates. These were not 138 independent bad assets. The authority loader now separates:

- A 1.2x threshold for detecting and repairing market-wide adjustment-ratio basis changes.
- A 1.5x threshold for excluding residual single-asset ratio jumps.

After this repair, adjustment-ratio and combined-move blockers both fell to zero.

### Price-Integrity Root Causes

Added a row-level price audit with these classifications:

- `outside_official_lifecycle`
- `adjustment_ratio_discontinuity`
- `combined_price_adjustment_move`
- `official_initial_price_discovery`
- `official_post_suspension_repricing`
- `raw_price_discontinuity`

Initial-price discovery requires the event to occur within the first five observed sessions and within 30 calendar days of the official list date. This preserved 14 plausible no-price-limit listing events as review evidence instead of misclassifying them as source failures.

Three BSE assets still had unexplained raw-price drops above 50%, 161-381 days after listing, with stable adjustment ratios and no suspension evidence. They are explicitly quarantined in `configs/cn_stock_price_integrity_quarantine_20260716.json`:

- `CN_XBEI_920270`
- `CN_XBEI_920593`
- `CN_XBEI_920663`

The quarantine embeds row-level evidence and the SHA-256 of the audit that produced it.

### Manifest Binding

The CN stock data manifest is now schema version 5. It accepts asset-session and price-integrity packets, then validates:

- Expected audit stage.
- Same local generation date, including correct UTC-to-local conversion.
- Matching authority source root.
- Research-to-paper live boundary.
- Packet status and blocker list.
- Packet path and SHA-256 provenance.

A blocked packet blocks the manifest. A review-required packet can only produce a review-required manifest. When a specialized price packet is attached, the old generic extreme-return warning is replaced by explicit root-cause warnings.

### Research Runtime Debt

Two adjacent engineering findings were also fixed:

- Daily advisory factor generation now requests only the selected candidate factor names. Direct technical factors therefore use the existing dependency-pruned path instead of generating the entire factor family.
- Experiment fingerprint schema version 2 recursively follows 44 actual research dependency files. Unrelated GUI modules are excluded, while changes to imported research, factor, backtest, schema, and storage code still invalidate caches.

## Final Evidence

### Asset-Session Packet

- Status: `review_required`
- Bar rows: 6,512,719
- Assets: 3,853
- Raw gap rows: 133,162
- Official daily suspension rows: 127,296
- Official legacy suspension rows: 5,866
- Unresolved active sessions: 0
- Assets missing lifecycle metadata: 0
- Observed rows outside lifecycle: 0
- Review reason: `retrospective_legacy_suspension_evidence`
- Packet SHA-256: `e3edcd9dec4c78828028e9064d445babf3cc64069e0155db7219d8b902ffc6ea`

### Price-Integrity Packet

- Status: `review_required`
- Extreme adjusted-return rows: 63
- Blocking rows/assets: 0 / 0
- Official initial-price-discovery rows: 14
- Official post-suspension repricing rows: 49
- Lifecycle, ratio-jump, combined-move, and unexplained raw-price blockers: 0
- Packet SHA-256: `536d6db5a26b3b16fde0a11f284cda40fc44b6f141bfec5f0a98d807a4f859cb`

### Integrity-Bound Data Manifest

- Status: `review_required`
- Blockers: 0
- Bar rows/assets: 6,512,719 / 3,853
- Moneyflow rows/assets: 10,494,909 / 5,615
- Expected/bar/moneyflow market sessions: 2,674 / 2,674 / 2,674
- Missing whole-market bar sessions: 0
- Missing whole-market moneyflow sessions: 0
- Missing adjusted close, zero volume, and zero amount rows: 0
- Bar content SHA-256: `7594f76d84523ffa029bb1b41283faf3b5a7e552bca24c6f93d115fa8ed4ee63`
- Manifest SHA-256: `675b7eb270f2271a4389d254f2f91639473f867d4fe3e2a195262d016400ffa4`

The only manifest warnings are the two attached review-required packets and their three explicit review reasons.

## Verification

- Final complete suite after all runtime and structural optimizations: 2,178 tests passed in 654.558 seconds.
- The preceding full-suite run exposed one maintainability-only regression: `research_service.py` had grown to 2,945 lines against its 2,934-line ceiling. Candidate-factor request parsing was extracted into a focused module, reducing the service to 2,904 lines without relaxing the baseline.
- GUI and experiment-runner suites after dependency pruning and extraction: 103 tests passed.
- Python compilation: passed.
- Project audit: 2,736 files scanned; safety, syntax, mock boundaries, real data, and 82 factor configs passed.
- Readiness: Tushare and Parquet ready.
- Maintainability baseline: passed with known debt; no baseline regression remains.
- Research-family scheduler: ready; five CN ETF families allocate 100% of primary research budget; direct CN stock moneyflow remains 0% and `auxiliary_only`.

## Feasibility

| Question | Assessment |
| --- | --- |
| Can the repository continue reproducible factor research? | High feasibility |
| Can the cleaned CN stock view support auxiliary ETF features? | Yes, with review-required evidence acknowledged |
| Is direct CN stock moneyflow a valid primary research line? | No |
| Should the rejected residual-moneyflow grid be widened or retuned? | No |
| Is the next primary research direction available? | Yes: preregistered CN ETF family rotation under the scheduler |
| Is any result ready for live execution? | No, and live execution remains out of scope |

## Remaining Known Limitations

These are not hidden blockers from the scoped data remediation:

1. The 5,866 historical suspension gap rows rely on retrospective legacy evidence and therefore retain manual-review status.
2. The 63 extreme-return events are classified and non-blocking, but still require explicit review acknowledgement before a CN stock auxiliary run consumes the manifest.
3. The three quarantined BSE assets remain excluded until corrected provider history or independently verified corporate-action evidence is available.
4. The branch has not been merged into `main`. The project-completion gate is blocked only by `not_on_stable_branch`; office policy forbids pushing from this machine.
5. Maintainability debt remains: 13 modules exceed 1,000 lines, with `daily_trade_advisory.py` the largest. Refactoring them all in this data task would create unnecessary behavioral risk.
6. Test topology remains concentrated in unit tests: 548 unit files, two integration files, and zero E2E files. Adding empty files to improve the ratio would not improve assurance.
7. No paper manifest exists for the rejected residual-moneyflow family because no candidate qualified. Creating one would fabricate evidence.
8. The 2026 holdout remains sealed and must not be used for factor selection, threshold tuning, or rescue work.

## Next Direction

Start a new task from reviewed and integrated `main`, or from this branch only if integration has not yet occurred. Run the Quant PM startup gate, read this audit and the current research index, then use `configs/research_family_scheduler_cn_etf.json`.

Default primary family: `cn_etf_price_rotation`, the scheduler's highest-budget active family. Before implementation, perform a duplicate and stop-loss review against prior CN ETF rounds. Preregister a compact, economically distinct set of relative momentum, skip-momentum, and short-horizon reversal hypotheses. Run statistical prescreening before any portfolio grid, include cost/capacity/turnover constraints from the start, and keep the 2026 final holdout sealed.

If the duplicate/stop-loss review shows that price rotation is exhausted, rotate to the next scheduler family. Do not return to direct CN stock moneyflow selection.
