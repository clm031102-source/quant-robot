# Desktop Validation Evidence Closure Audit

Audit window: 2026-07-15 to 2026-07-16

Machine: `office_desktop`

Task: `factor_validation`

Branch: `codex/factor-validation-cn-stock-evidence-closure-20260715`

Research evidence source commit: `993656ed7726654e252b7240a74877c8308f1276`

Scope: provider calendar, authority CN stock bars and moneyflow, data-gap semantics, validation readiness, residual-moneyflow walk-forward evidence, market-regime coverage, promotion controls, performance, storage, and repository verification.

## Executive Verdict

The evidence-closure task is complete. The desktop profile now runs from provider-backed, fingerprinted authority inputs; all 38 rolling folds completed without a failed experiment case; the exact current case identities feed the regime-coverage and promotion gates; and the complete strict profile exits successfully.

The project is not complete as a trading product. It remains a pre-alpha research-to-paper platform. The frozen residual-moneyflow family produced `0 / 96` accepted candidates and `0 / 96` promotion candidates. No profitability, paper-readiness, or live-readiness claim is supported.

Known issues were either fixed in this branch or converted into explicit fail-closed review states. Material project debt still exists and is listed below; it was not hidden by weakening gates.

## Completion Assessment

The percentages below describe completion of a named engineering or research gate. They are not forecasts of return or probabilities of profitability.

| Dimension | Completion | Verdict |
| --- | ---: | --- |
| This evidence-closure task | 100% | Calendar, authority data, readiness, walk-forward, coverage, promotion, verification, and documentation were closed end to end |
| Reproducible desktop validation profile | 90% | Operational and fail-closed; remaining debt is runtime, broad code fingerprinting, and sparse integration/E2E topology |
| CN stock authority-data readiness | 75% | Whole-market coverage is complete, but 337,904 asset-session gaps still require PIT suspension/listing classification and extreme returns remain a warning |
| Frozen residual-moneyflow family evaluation | 100% evaluated | The full preregistered grid completed; the result is a complete rejection set |
| Frozen residual-moneyflow promotion readiness | 0% | All 96 candidates are blocked |
| Paper observation for this family | 0% | No candidate qualified for paper packaging |
| Live execution | 0% and out of scope | Broker, account, order, and automatic-live paths remain prohibited |

Overall stage: `pre-alpha / research-to-paper`, not project-complete.

## Fixed Findings

| Finding | Resolution |
| --- | --- |
| Calendar evidence was not provider-backed | Added a Tushare `trade_cal` artifact and tamper-checked manifest for synchronized SSE/SZSE sessions |
| Missing whole-market dates were mixed with stock-specific gaps | Added separate whole-market hard blockers and an explicit asset-level `review_required` policy |
| Authority manifests did not bind referenced datasets | Fingerprinted the authority bar and moneyflow configs, their referenced files, schemas, and content |
| Validation could run without a frozen evidence contract | Added same-day readiness binding for branch, task, factor list, config, data, calendar, manifests, and the 2025 cap |
| Walk-forward could use implicit or non-authority inputs | Rewired desktop validation to adjusted authority bars and the authority moneyflow config |
| Cached grids could be reused with incomplete case evidence | Cache reuse now requires the mode-specific evidence files and exact reproducibility fingerprints |
| Partial files could be mistaken for completed evidence | Case and fold artifacts are atomic; completion manifests are written last |
| Regime coverage could read stale extra case directories | Coverage now binds exact `(fold, case_id)` identities from the current `walk_forward_folds.csv` |
| Factor work was recomputed for every fold and case | One causal full-window factor matrix is built, then date-sliced and shared across folds |
| Unrequested factor dependencies consumed excessive memory | Moneyflow and technical factor construction now prune to the requested dependency set |
| Train and test cases retained unnecessary full diagnostics | Train cases keep fold-level manifests/leaderboards; test cases keep only `metrics.json` and `regime_curve.csv` |
| GUI HTTP integration could flake under full-suite load | Compute-heavy advisory requests now use a separate 60-second test budget; ordinary local HTTP checks remain at 15 seconds |
| Promotion reported missing provider evidence despite a generated status pack | Bound the residual-regime promotion config to the provider-status packet with a one-day freshness requirement |
| Overnight execution crossed a same-day startup boundary | The gate blocked the stale packet; both PM and factor-mining startup evidence were regenerated for 2026-07-16 |

## Authority Evidence

### Trading Calendar

- Provider and endpoint: Tushare `trade_cal`
- Requested range: 2015-01-01 to 2025-12-31
- Effective range: 2015-01-05 to 2025-12-31
- Synchronized sessions: 2,674 for both SSE and SZSE
- Calendar artifact SHA-256: `dbecac271ded4b95da6234658742177569405c477097ec1b780914ebddcaa11a`
- Exchange date SHA-256: `328469945237e66da6db654c9de8d0a698bb08b65c79bd872c94629d6eabb5ef`
- Status: `cleared`

### Bars And Moneyflow

- Bar rows: 8,450,716
- Bar assets: 4,726
- Bar market sessions: 2,674
- Moneyflow rows: 10,494,909
- Moneyflow assets: 5,615
- Moneyflow market sessions: 2,674
- Missing adjusted-close rows: 0
- Zero amount rows: 0
- Zero volume rows: 0
- Whole-market bar gaps: 0
- Whole-market moneyflow gaps: 0
- Data-manifest blockers: 0
- Data-manifest status: `review_required`
- Remaining manifest warning: `extreme_return_rows_present`

Local authority repairs added 36,810 adjusted bar rows across seven missing market dates and 47,963 moneyflow rows across ten missing market dates. Generated data and reports remain outside Git.

### Asset-Level Gap Review

- Asset-session gaps: 337,904
- Assets with gaps: 2,471 of 4,726
- Whole-market missing sessions: 0
- Review reason: `asset_sessions_require_suspension_review`
- Hard blockers: 0

These rows must not be filled mechanically. They require point-in-time classification as not-yet-listed, suspended, delisted, exchange transition, or true provider/data loss.

## Walk-Forward Evidence

Frozen grid:

- Factors: 4
- Top-N values: 5, 10, 20
- Cost values: 20 and 30 bps
- Regime lookbacks: 120, 150, 180, 252
- Cases: 96
- Rolling folds: 38
- Train/test window design: 252 / 63 trading days with a 63-day step
- Evidence horizon: 2015-2025; the 2026 final holdout was not opened

Execution totals:

| Side | Cases | Completed | No trades | Failed |
| --- | ---: | ---: | ---: | ---: |
| Train | 3,648 | 2,344 | 1,304 | 0 |
| Test | 3,648 | 2,992 | 656 | 0 |

Aggregate outcome:

- Accepted candidates: 0
- Rejected candidates: 96
- Individually accepted fold rows: 69 of 3,648
- Rejected fold rows: 3,579 of 3,648
- Promotion status: 96 blocked, 0 research-only, 0 paper-ready, 0 manual-live-review

The highest-ranked aggregate row was `CN_large_minus_liquidity_20_top5_cost20_reb1_regime252`. Its diagnostic mean test Sharpe was 2.181 and mean test relative return was 18.42%, but it accepted `0 / 38` folds, reached a -39.13% worst test drawdown, had 293 capacity-rejected trades, and had adjusted IC p-value 1.0. The headline Sharpe is therefore not usable evidence.

Candidate-level rejection counts:

| Reason | Candidates |
| --- | ---: |
| Capacity-rejected trades present | 96 |
| Insufficient OOS trades in one or more folds | 96 |
| Relative return below threshold in one or more folds | 96 |
| OOS Sharpe below threshold in one or more folds | 96 |
| Train not completed in one or more folds | 96 |
| Test not completed in one or more folds | 96 |
| Adjusted IC significance not passed | 96 |
| Drawdown above limit | 90 |
| Insufficient accepted folds | 77 |

`train_not_completed`, `test_not_completed`, and `insufficient_oos_trades` are aggregate fail-closed labels caused by no-trade or rejected folds; they do not indicate program crashes. Program-level failed cases were zero.

## Regime And Promotion Evidence

Market-regime coverage is sufficient and exactly bound to current walk-forward identities:

- Rows: 23,647
- Observation range: 2015-01-05 to 2025-11-21
- Allowed rows: 13,610
- Blocked rows: 10,037
- Regimes: bear, bull, sideways
- Regime counts: 6,516 bear, 12,684 bull, 1,864 sideways
- Coverage blockers: 0

The promotion gate still blocks every candidate. The universal blocking reasons include IC significance, positive-IC rate, adjusted IC, tail IC, distinct regime-lookback robustness, walk-forward acceptance, and uncleared asset-level data review. Provider readiness is now present and fresh; it is no longer reported as missing.

## Performance And Storage

- Full cold validation runtime: 20,201.36 seconds, about 5 hours 37 minutes
- Final strict profile after evidence existed: 910.40 seconds, about 15 minutes 10 seconds
- Post-prune validation, coverage, promotion, and summary replay: 136.32 seconds
- Earlier projected runtime before reuse work: more than 10 hours
- Naive full-window factor peak: about 42 GB and stopped
- Final cold peak after dependency pruning: about 22 GB
- Stable later-fold memory: about 15-17 GB
- Gap-audit runtime improved from roughly six minutes to about 39 seconds

Evidence storage cleanup:

- Before: 124,340 files, 1.556 GB
- After: 7,604 files, 0.091 GB
- Removed: 3,648 stale train case directories and 54,720 stale test diagnostic files
- Preserved: 3,648 test metrics, 3,648 regime curves, 38 train manifests, 38 test manifests, all fold leaderboards, and final walk-forward outputs

## Verification Record

- Complete unit/integration suite: 2,137 tests passed
- Focused validation and evidence suites: 152 tests passed during implementation
- Promotion gate and CLI suites after provider binding: 29 tests passed
- Python compilation: passed
- Project audit: 2,716 files scanned, all configured checks passed
- Factor configs: 82 scanned; no invalid files, unknown factors, unsupported sources, or window mismatches
- Calendar validation: passed
- Strict `desktop-validation` profile: passed end to end
- Post-prune cache, regime coverage, promotion, and summary replay: passed
- Maintainability regression gate: passed its baseline

## Feasibility

| Question | Assessment |
| --- | --- |
| Can this repository continue reproducible factor research? | High feasibility |
| Can the desktop rerun this frozen profile safely? | High feasibility, with a multi-hour cold runtime |
| Is the authority dataset ready for unrestricted promotion? | No; asset-level suspension/listing review remains |
| Is this residual-moneyflow family worth parameter retuning? | No; the complete grid failed every aggregate candidate |
| Is any candidate ready for paper observation? | No |
| Is any candidate ready for real money or automated execution? | No, and those paths are out of scope |

## Remaining Known Issues

Priority 0:

1. Classify all 337,904 asset-session gaps with point-in-time listing, suspension, delisting, and exchange-transition evidence. Keep promotion blocked until unexplained gaps are zero.
2. Audit `extreme_return_rows_present` against corporate actions, adjustment factors, listing events, and source errors.
3. Keep the frozen residual-moneyflow family closed. Do not reinterpret aggregate Sharpe as acceptance and do not widen the same parameter grid.
4. Keep 2026 sealed as the final holdout. It must not become a tuning set.

Priority 1:

1. The maintainability audit reports 13 modules above 1,000 lines. The largest is `src/quant_robot/ops/daily_trade_advisory.py` at 13,982 lines.
2. Test topology is 541 unit files, two integration files, and zero E2E files. The baseline passes, but integration and E2E coverage remain structurally weak.
3. The daily advisory still computes a broad technical factor set synchronously. The wider test timeout prevents false failures but does not replace a production dependency-pruning optimization.
4. The experiment code fingerprint currently hashes the whole Python package. Unrelated GUI source edits can invalidate expensive research caches; a narrower, fail-closed research dependency fingerprint needs a separately reviewed design.
5. Paper manifests are absent because no candidate qualified. No paper-performance evidence exists for this family.

Governance constraints:

- Primary research market remains `CN_ETF`.
- Direct CN stock moneyflow remains `auxiliary_only` and must not consume the primary research budget.
- Research-to-paper only: no broker connection, account reads, order placement, or automatic live trading.

## Recommended Next Direction

Run a dedicated `data_pipeline` task to close point-in-time CN stock suspension/listing evidence and the extreme-return audit. Do not retune this rejected residual-moneyflow family. Once data review is either cleared or documented as an external provider blocker, return the primary research budget to a preregistered CN ETF family with a genuinely orthogonal hypothesis.
