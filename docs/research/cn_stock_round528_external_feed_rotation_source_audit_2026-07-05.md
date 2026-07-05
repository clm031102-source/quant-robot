# CN Stock Round528 External Feed Rotation Source Audit

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 25 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run portfolio grids, and did not touch final holdout. It used local processed external-feed data to define the boundary for any future PIT-source rotation while analyst-report April cache remains blocked.

## Round Objective

Round527 prepared the frozen January-April analyst-report prescreen path, but April cache remains blocked on 2026-07-05 by missing required cross-machine quota evidence and same-day provider request budget exhaustion.

The Round528 objective was therefore:

- avoid repeating a same-day analyst-report quota dry-run without new quota evidence;
- inspect an alternate PIT-source rotation path without provider calls;
- verify whether local external-feed processed data has improved enough to justify a source-audit review;
- keep prior northbound and margin-credit failures hibernated unless a new independent review explicitly reopens them.

No review agents were created in this round because the next required review-agent checkpoint is round 30 after the Round504 baseline, due in Round533.

## Startup Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 04:31 +08:00.
- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Git status before work: clean and synchronized with origin.
- Remote branches: `origin/main` and `origin/codex/factor-batch-cn-stock-profit-mining-20260704`.
- Startup context: clear, branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Local External-Feed Coverage Audit

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_coverage_audit.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --output-dir data\reports\round528_external_feed_coverage_audit_20260705 --market CN
```

Result:

- Stage: `external_feed_coverage_audit`
- Processed root: `data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623`
- Audited feeds: 2
- Pass feeds: 1
- Blocked feeds: 1
- External-feed IC or portfolio allowed: false
- Blocker: `lpr_non_missing_coverage_below_threshold`
- Promotion allowed: false

HK hold result:

- Status: pass
- Rows: 134,461
- Observation dates: 40
- First/last date: 2024-07-02 to 2025-12-31
- Unique symbols: 3,980
- Median gap days: 1.0
- Detected frequency: `daily_or_near_daily`
- Missing `hold_ratio`: 0
- Missing `hold_vol`: 0
- Allowed use: `daily_cross_sectional_rank_after_full_validation`

Macro rates result:

- Status: blocked
- Rows: 340
- Observation dates: 340
- First/last date: 2024-07-01 to 2025-12-31
- SHIBOR complete rows: 340
- LPR 1Y non-null rows: 0
- LPR 5Y non-null rows: 0
- LPR non-null ratio: 0.00%
- Allowed use: `shibor_only_regime_control_after_long_cycle_validation`

Interpretation:

- HK hold source coverage has improved enough to be reviewed as source-quality evidence.
- LPR-dependent macro/liquidity factors remain blocked.
- A coverage audit is not IC evidence, portfolio evidence, promotion evidence, or live evidence.

## Join Smoke Evidence

An attempted full-window join smoke from 2024-07-01 to 2025-12-31 exceeded the local command timeout. This matches the known performance caveat in earlier external-feed review docs: the join-smoke implementation loops over signal dates and recomputes latest eligible observations. No conclusion should be drawn from the timed-out full-window attempt.

The minimal controlled smoke used July 2024 only:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round528_external_feed_join_smoke_202407_20260705 --market CN --signal-start-date 2024-07-01 --signal-end-date 2024-07-31
```

Result:

- Stage: `external_feed_factor_matrix_join_smoke`
- Seed count: 6
- Pass count: 6
- Fail count: 0
- Insufficient-history count: 0
- Joined rows: 428,856
- Available-date violations: 0
- Same-day or future raw-date violations: 0
- Promotion allowed: false

Seed-level status:

| Seed | Status | Joined rows | Signal dates | Unique symbols | PIT violations |
| --- | --- | ---: | ---: | ---: | ---: |
| `margin_financing_acceleration_exhaustion_20` | pass | 117,263 | 30 | 3,925 | 0 |
| `margin_balance_crowding_reversal_20` | pass | 117,263 | 30 | 3,925 | 0 |
| `northbound_hold_ratio_accumulation_20` | pass | 97,135 | 29 | 3,355 | 0 |
| `northbound_hold_accumulation_flow_regime_20` | pass | 97,135 | 29 | 3,355 | 0 |
| `index_location_value_liquidity_regime_20` | pass | 30 | 30 | n/a | 0 |
| `shibor_liquidity_tightening_regime_20` | pass | 30 | 30 | n/a | 0 |

Interpretation:

- The local short-window available-date join path is clean.
- This does not override the coverage audit's LPR blocker.
- This does not override prior negative northbound and margin-credit factor evidence.
- This is not a reason to run a portfolio grid or promotion gate.

## Rotation Boundary

External feed may be used next only as a source-review object, not as an immediate factor-mining family.

Required review before any new external-feed preregistration:

- Read Round190-192 external-feed review.
- Read Round213 external northbound crowding/reversal prescreen.
- Read Round450-452 audit language that blocks old northbound/margin revival without new independent data-quality proof.
- Read this Round528 coverage audit.
- Separate source-quality changes from factor-family evidence.

Allowed next external-feed work:

- Write a family review deciding whether HK hold coverage improvement is a sufficiently new source-quality fact.
- If reopened, preregister only a genuinely new HK-hold structure with frozen formula direction before testing.
- Treat SHIBOR as a possible regime-control input only after long-cycle validation.
- Keep LPR-dependent factors blocked until LPR non-missing coverage is repaired.

Blocked external-feed work:

- No old positive northbound accumulation rerun as a direct rank.
- No old northbound crowding/reversal rerun without a new mechanism.
- No margin-credit reentry without a fresh review of prior failures.
- No LPR factor or policy-liquidity LPR regime until LPR coverage clears.
- No portfolio grid, promotion gate, or final-holdout read from source audit or join smoke.

## Decision

Round528 does not rotate away from analyst-report revision yet. The primary analyst path is still: collect required quota-pack evidence, wait for an actual-date preflight exit `0`, cache April once, and run the frozen January-April prescreen.

If analyst-report cache remains blocked, the next useful non-provider action is an external-feed family review that treats Round528 as source-quality evidence only. The likely allowed review object is HK-hold coverage improvement; LPR/macro remains blocked, and old northbound/margin factor families remain hibernated unless the review explicitly proves a new hypothesis.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run external-feed portfolio grids or promotion gates from coverage audit or join smoke.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
