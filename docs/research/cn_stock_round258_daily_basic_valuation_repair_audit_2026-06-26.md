# CN Stock Round258 Daily-Basic Valuation Repair Audit

- Date: 2026-06-26
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining, not CN ETF rotation
- Stage: coverage repair and industry/style exposure audit
- Final holdout: excluded

## Objective

Round258 audited the strongest Round257 diagnostic line:

`daily_basic_valuation_reversion_quality_60`

Round257 showed strong full-sample 20-day IC, but the original factor failed the required-field clean coverage gate because `dv_ttm` coverage was weak. Round258 therefore tested only one pre-registered repair path: replace `dv_ttm` with `dv_ratio`, then re-run full-sample prescreen and industry/style exposure audit.

This round did not run portfolio grid search and does not permit promotion.

## Candidate Gate

- Candidate plan: `configs/factor_mining_candidate_plan_round258_daily_basic_valuation_reversion_repair_audit_20260626.json`
- Gate output: `data/reports/round258_daily_basic_valuation_reversion_repair_candidate_plan_gate_20260626`
- Gate status: research_ready
- Candidates: 2
- Complete control areas: 8 / 8
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false

## Coverage Audit

- Output: `data/reports/round258_daily_basic_valuation_coverage_audit_20260626`
- Data window: 2015-01-05 to 2025-12-31
- Rows: 10,810,505
- Assets: 5,707
- Gate status: repair_ready

| Factor | Required Fields | Full Coverage | Date Pass | Low Fields | Repair Ready |
|---|---|---:|---:|---|---|
| daily_basic_valuation_reversion_quality_60 | pb, ps_ttm, dv_ttm | 0.6837 | 0.0000 | dv_ttm | yes |
| daily_basic_valuation_dispersion_compression_60 | pb, pe_ttm, dv_ratio | 0.7470 | 0.2519 | pe_ttm | yes |

Replacement checks:

| Missing Field | Replacement | Non-null | Date Pass | Pass |
|---|---|---:|---:|---|
| dv_ttm | dv_ratio | 0.9116 | 1.0000 | yes |
| pe_ttm | pe | 0.8597 | 0.8462 | yes |

Interpretation: the `dv_ttm -> dv_ratio` substitution is coverage-justified before any portfolio evidence, so the repaired valuation candidate was allowed to proceed to a fresh prescreen and exposure audit.

## Repaired Candidate Prescreen

- Candidate: `daily_basic_valuation_reversion_dvratio_quality_60`
- Output: `data/reports/round258_daily_basic_valuation_reversion_dvratio_full_sample_prescreen_20260626`
- Data window: 2015-01-05 to 2025-12-31
- Factor rows: 10,700,940
- Aligned rows: 21,226,578
- Coverage pass: yes
- FDR-significant tests: 2 / 2
- Strict research leads: 0
- Promotion candidates: 0

| Horizon | IC | ICIR | t | IC>0 | Q5-Q1 | Mono | Field Clean | Capacity Clean | Lead |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 0.0661 | 0.533 | 27.44 | 69.8% | 0.0137 | 0.40 | 90.5% | 94.8% | no |
| 5 | 0.0508 | 0.415 | 21.42 | 66.3% | 0.0008 | 0.10 | 90.5% | 94.8% | no |

The repair kept the raw IC and fixed coverage, but it damaged the portfolio translation signal: Q5-Q1 became small and monotonicity dropped sharply.

## Shape And Exposure Audit

Primary all-status stock-basic audit:

- Output: `data/reports/round258_daily_basic_valuation_shape_exposure_audit_all_status_20260626`
- Stock-basic rows: 5,855
- Includes L and D list statuses from Round198 metadata.
- Shape pass count: 0
- Residual candidate factors: 0
- Exposure pass: false

Quantile shape at h20:

| Q1 | Q2 | Q3 | Q4 | Q5 | Q5-Q1 | Mono | Best | Pass |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 0.0459 | 0.0820 | 0.1082 | 0.1150 | 0.0595 | 0.0137 | 0.40 | Q4 | no |

Exposure summary:

| Raw IC | Residual IC | Residual t | Residual Retention | Residual IC>0 | Max Style Corr | Industry R2 | Style Coverage | Missing Industry |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0661 | 0.0151 | 12.26 | 0.229 | 61.3% | 0.9479 | 0.1612 | 89.6% | 3.8% |

The same audit was first run with L-only stock_basic and then repeated with L+D all-status metadata. The all-status rerun reduced industry-missing rows slightly but did not change the conclusion.

## Decision

- Promotable factors: 0
- Strict research leads: 0
- Repaired diagnostic candidates worth portfolio conversion: 0
- Family decision: hibernate the direct daily-basic valuation-reversion repair line.

The decisive failures are:

- Q5 is not the best bucket.
- Quantile monotonicity is only 0.40.
- Residual IC falls from 0.0661 to 0.0151 after industry/style residualization.
- Residual retention is only 22.9%, below the 35% residual-candidate threshold.
- Max style correlation is 0.9479, consistent with a strong value/style exposure rather than clean alpha.

## Next Direction

Round259 must rotate away from daily-basic valuation repair and choose a genuinely orthogonal family. Forbidden next work:

- no `daily_basic_valuation_reversion_dvratio_quality_60` portfolio grid;
- no `dv_ratio` weight tuning;
- no sign flip;
- no loosening quantile-shape, style-coverage, or residual-retention thresholds;
- no promotion from raw IC/FDR alone.

The next family should be non-daily-basic and non-forecast, with full-sample PIT controls and industry/style residual checks from the start.
