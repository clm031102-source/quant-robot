# CN Stock Round240 Accounting Quality Repaired Candidate Prescreen

Date: 2026-06-25

## Objective

After the five raw accounting-quality formulas produced zero residual IC research leads, run one repaired-candidate pass using simple public-accounting intuition:

- industry-relative cash/accrual quality;
- size/liquidity residual asset-growth quality;
- a balanced two-sleeve composite.

This is still an IC/FDR/neutralization gate only. It is not a portfolio, Sharpe, return, win-rate, drawdown, paper-ready, or live-trading claim.

## Inputs

- Statement roots: same 115-symbol PIT statement sample as Round239.
- Bars: `data/processed/cn_stock_long_history_2015_202306` and `data/processed/office_desktop_20260616_combined_research`.
- Daily-basic context: `data/processed/cn_stock_long_history_2015_202306` and `data/processed/office_desktop_20260617_daily_basic_factor_inputs`.
- Stock basic: `data/processed/cn_stock_metadata`.
- Output: `data/reports/round240_accounting_quality_repaired_candidate_prescreen_115_symbol_20260625`.

## Result

| Item | Value |
|---|---:|
| Repaired candidates | 3 |
| Factor rows | 4,552 |
| Label rows | 585,163 |
| Aligned rows | 9,104 |
| Tests | 6 |
| FDR-significant tests | 0 |
| Neutral-gate pass tests | 0 |
| Research leads | 0 |
| Promotion allowed candidates | 0 |

## Top Rows

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `aq_repaired_industry_relative_cash_accrual_quality` | 5 | 0.0291 | 0.328 | 1.67 | 38.5% | -0.0021 | 0.3030 | 0.0197 | 0.0117 | reject |
| `aq_repaired_industry_relative_cash_accrual_quality` | 20 | 0.0257 | 0.240 | 1.23 | 34.6% | -0.0111 | 0.3636 | 0.0048 | 0.0156 | reject |
| `aq_repaired_size_liquidity_residual_asset_growth_quality` | 5 | 0.0252 | 0.161 | 0.88 | 46.7% | 0.0062 | 0.8485 | 0.0204 | 0.0243 | reject |
| `aq_repaired_size_liquidity_residual_asset_growth_quality` | 20 | 0.0234 | 0.120 | 0.66 | 56.7% | -0.0066 | -0.1818 | 0.0200 | 0.0267 | reject |
| `aq_repaired_balanced_cash_asset_quality` | 20 | 0.0197 | 0.101 | 0.56 | 58.1% | -0.0080 | -0.1818 | 0.0185 | 0.0221 | reject |
| `aq_repaired_balanced_cash_asset_quality` | 5 | 0.0128 | 0.080 | 0.45 | 45.2% | 0.0053 | 0.8485 | 0.0062 | 0.0102 | reject |

## Audit

The repaired pass improved the best raw IC shape slightly, but it did not create a usable lead. The strongest repaired row still fails FDR and has a negative top-minus-bottom quantile spread. That combination is important: the factor has a mild cross-sectional correlation, but the actual ranked portfolio shape is not clean enough to justify a portfolio conversion.

The limiting issue is not a missing portfolio setting. It is alpha-shape weakness under multiple testing and neutralization. Parameter tuning around these three repaired candidates would be data mining.

## Decision

No repaired accounting-quality candidate is promoted to walk-forward, portfolio grid, paper-ready, or live use.

Allowed next work:

1. Continue PIT statement sample expansion if the objective is to test accounting quality with adequate cross-sectional power.
2. Rotate to a different accounting-quality substructure, such as revision surprise, abnormal accrual change, or event-window post-announcement drift.
3. Keep the same formula-smoke, label-smoke, residual IC, multiple-testing, cost/capacity, regime, and final-holdout gates.

Blocked:

- no Sharpe/profit/win-rate claim from Round240;
- no portfolio conversion for the three repaired candidates;
- no final holdout access.
