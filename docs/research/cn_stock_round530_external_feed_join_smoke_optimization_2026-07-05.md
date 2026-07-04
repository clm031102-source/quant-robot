# CN Stock Round530 External Feed Join-Smoke Optimization

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 27 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, and did not touch final holdout. It fixed the local full-window external-feed join-smoke performance blocker recorded in Round528.

## Round Objective

Round528's full-window external-feed join smoke timed out. Round529 then decided that external-feed families remain hibernated unless a genuinely new mechanism is preregistered. Round530 therefore focused only on source tooling:

- make the long-window join smoke complete locally;
- preserve available-date PIT semantics;
- preserve Round528 short-window outputs;
- keep promotion and factor-family decisions blocked.

No review agents were created in this round because the next required review-agent checkpoint is round 30 after the Round504 baseline, due in Round533.

## Startup Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 04:50 +08:00.
- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Git status before work: clean and synchronized with origin.
- Startup context: clear, branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Root Cause

The previous join-smoke implementation looped over every signal date. For each date, it filtered the full feed by `available_date <= signal_date`, sorted, and dropped duplicates to find the latest observation per symbol.

That made the long-window path scale roughly with:

```text
number_of_signal_dates * feed_rows
```

The repeated full-feed filtering and sorting was the likely cause of the Round528 full-window timeout.

## Implementation

Changed:

- `src/quant_robot/ops/external_feed_factor_matrix_join_smoke.py`
- `tests/unit/test_external_feed_factor_matrix_join_smoke.py`

Key implementation points:

- Added `_latest_observations_for_signal_dates`.
- The helper groups by `symbol` or `index_symbol`, then uses `pd.merge_asof` to align all signal dates to the latest `available_date` in one pass per key.
- Market-level feeds without `symbol` or `index_symbol` use the same multi-date as-of path without a key.
- Dates are normalized to `datetime64[ns]` before `merge_asof` to avoid pandas merge-key precision mismatches.
- Repeated processed-feed reads are cached by `(feed_name, market)` across seeds.
- Existing report fields and promotion blockers are preserved.

## Test-First Evidence

New failing tests were added before implementation:

- `test_latest_observations_for_signal_dates_aligns_all_dates_in_one_pass`
- `test_join_smoke_reads_shared_processed_feed_once_across_seeds`

Observed red evidence:

- The multi-date helper test initially failed because `_latest_observations_for_signal_dates` did not exist.
- The shared-feed cache test initially failed because `external_margin_detail` was read twice for two seeds.

Focused green evidence:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_external_feed_factor_matrix_join_smoke tests.unit.test_external_feed_factor_matrix_join_smoke_cli
```

Result:

- 7 tests passed.

## Local Full-Window Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round530_external_feed_join_smoke_full_window_cached_20260705 --market CN --signal-start-date 2024-07-01 --signal-end-date 2025-12-31
```

Result:

- Runtime: about 61 seconds.
- Seed count: 6.
- Pass count: 6.
- Joined rows: 8,559,540.
- Available-date violations: 0.
- Same-day or future raw-date violations: 0.
- First joined signal date: 2024-07-02 for margin, index, and SHIBOR; 2024-07-03 for HK-hold.
- Last joined signal date: 2025-12-31.
- Promotion allowed: false.

This is source-tooling evidence only. It is not IC evidence, portfolio evidence, promotion evidence, or live evidence.

## Round528 Regression Evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round170_20260623.json --output-dir data\reports\round530_external_feed_join_smoke_202407_regression_20260705 --market CN --signal-start-date 2024-07-01 --signal-end-date 2024-07-31
```

Result matched Round528:

- Seed count: 6.
- Pass count: 6.
- Joined rows: 428,856.
- Available-date violations: 0.
- Same-day or future raw-date violations: 0.

## Decision

Round530 removes a source-tooling blocker but does not reopen external-feed factor mining.

The external-feed family boundary from Round529 remains active:

- old positive northbound accumulation remains hibernated;
- old northbound crowding/reversal remains hibernated;
- margin-credit remains hibernated after Round193 residual collapse;
- LPR/macro-rate factors remain blocked until LPR non-missing coverage is repaired;
- SHIBOR is allowed only as a possible regime-control review after long-cycle validation;
- no portfolio grid, promotion gate, or final-holdout read is allowed from join-smoke evidence.

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
