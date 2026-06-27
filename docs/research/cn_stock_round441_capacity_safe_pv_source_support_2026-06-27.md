# CN Stock Round441 Capacity-Safe PV Source Support

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

After RSRS and SuperTrend failed formal rebuild, the sprint rotated away from ordinary public technical overlays and moved to the historically stronger capacity-safe price-volume family.

Round441 made two reusable improvements:

1. `shortlist_public_factor_source` can now materialize capacity-safe price-volume factors for shortlist trade dates.
2. `simulation_shortlist_cohort_entry_timed` can now run an incremental overlay mode on existing pre-overlay trade rows, instead of replacing the current Alpha101/Dragon baseline.

## Code Changes

Files changed:

- `src/quant_robot/ops/shortlist_public_factor_source.py`
- `src/quant_robot/ops/simulation_shortlist_cohort_entry_timed.py`
- `scripts/run_simulation_shortlist_cohort_entry_timed.py`
- `tests/unit/test_shortlist_public_factor_source.py`
- `tests/unit/test_simulation_shortlist_cohort_entry_timed.py`

New capabilities:

- registered `capacity_safe_price_volume` factors in the public-factor source registry;
- added CLI `--weight-column`;
- added CLI `--disable-dragon-cash-filter`;
- made `_build_trade_rows` drop stale `final_*` columns before recomputing event exposure, which allows a prior candidate's `cohort_trade_rows.csv` to be used as input safely.

Tests:

- added failing-first test for `range_contraction_lowvol_reversal_20` source support;
- added failing-first test for disabled Dragon cash plus existing pre-overlay weight columns;
- added regression coverage for stale `final_*` columns.

Verification:

- `python -m unittest tests.unit.test_shortlist_public_factor_source`
- `python -m unittest tests.unit.test_simulation_shortlist_cohort_entry_timed tests.unit.test_simulation_shortlist_cohort_entry_timed_cli`

## Factor Source

Materialized source:

- `data/reports/round441_24h_profit_sprint_capacity_safe_pv_range_contraction_source_20260627/public_factor_values_for_shortlist.parquet`

Factor:

- `range_contraction_lowvol_reversal_20`

Coverage:

- target trade pairs: 26,450;
- matched values: 26,400;
- missing share: 0.189%;
- bar rows used: 10,785,537;
- bar assets: 5,707.

## Decision

Use this new source support for formal incremental overlay tests only. Do not treat the historical IC prescreen alone as portfolio evidence.

Next step:

- Round442 formally tests `range_contraction_lowvol_reversal_20` as a second-layer overlay on top of the current delayed-exit Alpha101/Dragon baseline.
