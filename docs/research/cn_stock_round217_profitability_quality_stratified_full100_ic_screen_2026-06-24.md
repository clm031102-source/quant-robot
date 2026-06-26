# CN Stock Round217 Profitability Quality Stratified Full100 IC Screen

Round217 reran the profitability-quality family on a stratified 100-symbol `fina_indicator`
shard after the Round216 PIT signal-date filter and timing audit passed. This was a
controlled IC screen only. It does not allow portfolio grids, promotion, or live use.

## Inputs

- Financial root: `data/processed/round216_financial_pit_signal_filtered_stratified_shard1_full100_20260624`
- Preregistration report: `data/reports/round217_profitability_quality_preregistration_stratified_shard1_full100_20260624`
- Factor matrix smoke: `data/reports/round217_profitability_quality_factor_matrix_smoke_stratified_shard1_full100_20260624`
- Controlled IC screen: `data/reports/round217_profitability_quality_controlled_ic_screen_stratified_shard1_full100_20260624`
- Horizons: 5 and 20 trading days
- Execution lag: 1 trading day
- Minimum cross-section: 30

## Coverage And Alignment

- Assets: 100
- Financial rows after PIT signal filtering: 4,277
- Pre-registered candidates: 14
- Coverage-passed candidates: 14
- Coverage-failed candidates: 0
- Factor value rows: 57,970
- Label-aligned rows: 115,940
- Label coverage: 96.81%
- Alignment violations: 0

The data path is usable for controlled financial-factor research on this shard:
announcement timing, stale signal lag, duplicate financial keys, and label alignment
passed the current checks.

## Controlled IC Results

- Tests: 28
- IC observations: 1,204
- Bonferroni-significant tests: 0
- FDR-significant tests: 0
- Research leads: 0
- Promotion allowed: false

The strongest absolute IC rows were:

| Factor | Horizon | IC Mean | ICIR | t-stat | p-value | Positive IC Rate | Multiple-testing result |
|---|---:|---:|---:|---:|---:|---:|---|
| `fina_roa_persistence_4q` | 5 | -0.0384 | -0.310 | -1.99 | 0.0471 | 43.90% | rejected |
| `fina_roe_persistence_4q` | 5 | -0.0312 | -0.242 | -1.55 | 0.1207 | 39.02% | rejected |
| `fina_roa_level` | 5 | -0.0248 | -0.195 | -1.29 | 0.1961 | 36.36% | rejected |
| `fina_gross_margin_level` | 20 | 0.0232 | 0.186 | 1.23 | 0.2177 | 54.55% | rejected |
| `fina_cash_earnings_quality_ratio` | 20 | 0.0141 | 0.112 | 0.74 | 0.4588 | 54.55% | rejected |

The negative sign on several profitability persistence rows is diagnostic only. It is
not permission to flip factor direction after seeing the result. Any inverse-profitability
hypothesis would require a new pre-registration with a separate economic thesis.

## Decision

- Useful factor candidates found: 0
- Promotable factors found: 0
- Portfolio grid allowed: false
- Family decision: hibernate direct profitability-quality formula tuning for now.
- Data decision: keep the stratified PIT financial data path; it is useful infrastructure.
- Next direction: rotate away from direct profitability-quality and run a fresh family
  selection before new factor generation.

## Process Update

Before the next mining round, the startup gate must confirm the method-control suite:
A-share trading constraints, financial availability timing, industry/style neutral
combination, ETF signal boundary, portfolio metric pack, strict statistics, China market
regime coverage, and event-factor controls. Short-window or single-shard signals remain
insufficient for profit claims.

