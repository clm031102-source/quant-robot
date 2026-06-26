# Round98 Profitability Quality Controlled IC Screen Design - 2026-06-22

## Objective

Test the 14 pre-registered CN stock profitability-quality candidates from Round96 on the clean Round95 100-symbol `fina_indicator` shard, using the Round97 point-in-time factor matrix and label-alignment path.

This round is a diagnostic IC screen only. It must not promote factors, run a portfolio backtest, tune parameters, or claim profitability.

## Data Inputs

- Financial input: `data/processed/tushare_fina_indicator_shard1_full100_backfill_round95_20260622`
- Price inputs:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260616_combined_research`
- Candidate registry: `data/reports/profitability_quality_preregistration_round96_20260622/profitability_quality_preregistration.json`

## Method

- Build factor values only from pre-registered profitability-quality specs.
- Use `ann_date` as information availability date.
- Align each financial event to the next tradable signal date.
- Use execution lag 1 so forward labels begin after signal availability.
- Group IC observations by `factor_name`, `horizon`, and `end_date`.
- Compute cross-sectional Spearman IC only when the cross-section has at least 30 assets.
- Require at least 8 IC observations per factor-horizon result.
- Apply both Bonferroni and Benjamini-Hochberg FDR correction across all tested factor-horizon pairs.

## Gate

Promotion is blocked unless a candidate survives multiple-testing controls and is explicitly marked as a research lead after multiple testing. Single-shard IC evidence is still not enough for paper readiness; it can only allow robustness and portfolio-translation checks.

## Expected Decision

- If one or more candidates survive multiple testing: move to lead robustness and factor-correlation audit.
- If no candidate survives multiple testing: do not tune the same family; prepare a family rejection and rotation audit.
