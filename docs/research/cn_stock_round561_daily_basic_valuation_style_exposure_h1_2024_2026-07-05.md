# CN Stock Round561 Daily-Basic Valuation Style Exposure H1 2024

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: explain the Round560 daily-basic failure mode by rerunning the existing daily-basic valuation shape/exposure audit over the same H1 2024 window.

## Run Window

| Field | Value |
| --- | --- |
| Script | `scripts\run_daily_basic_valuation_shape_exposure_audit.py` |
| Bars root | `data\processed\office_desktop_20260616_combined_research` |
| Daily-basic root | `data\processed\office_desktop_20260617_daily_basic_factor_inputs` |
| Stock-basic snapshot | `data\reports\round212_stock_basic_snapshot_20260624\metadata\tushare_stock_basic\list_status=L\snapshot=2026-06-24\part-00000.parquet` |
| Output | `data\reports\round561_daily_basic_valuation_shape_exposure_audit_h1_2024_20260705` |
| Start | 2024-01-02 |
| End | 2024-06-28 |
| Horizon | 20 |
| Execution lag | 1 |
| Min dates | 80 |
| Min cross-section | 100 |

## Data

| Metric | Value |
| --- | ---: |
| Bar rows | 625,434 |
| Daily-basic rows | 625,434 |
| Factor rows | 625,434 |
| Label rows | 512,600 |
| Style factor rows | 625,434 |
| Stock-basic rows | 5,528 |

## Summary

| Metric | Value |
| --- | ---: |
| Overall passes | false |
| Shape pass count | 1 |
| Exposure passes | false |
| Residual candidate factors | 0 |

Blockers:

- `no_residual_candidate_after_lightweight_exposure_audit`
- `style_coverage_below_threshold`

## Shape Result

The repaired valuation factor has clean H1 shape by raw quantiles:

| Factor | Horizon | Q1 | Q2 | Q3 | Q4 | Q5 | Q5-Q1 | Mono | Best | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `daily_basic_valuation_reversion_dvratio_quality_60` | 20 | -0.0484 | -0.0293 | -0.0224 | -0.0149 | -0.0040 | 0.0443 | 1.000 | q5 | true |

This is not enough for promotion because the exposure audit fails.

## Exposure Result

| Metric | Value |
| --- | ---: |
| Classification | `style_or_industry_exposure_dominated` |
| Raw rank IC | 0.1360 |
| Raw IC t-stat | 9.17 |
| Raw IC positive rate | 84.4% |
| Residual rank IC | -0.0489 |
| Residual IC t-stat | -6.28 |
| Residual positive rate | 30.3% |
| Residual retention ratio | 0.360 |
| Max absolute style correlation | 0.953 |
| Mean industry R2 | 0.157 |
| Style coverage ratio | 0.737 |
| Missing industry fraction | 0.0157 |

Style details:

| Style | Mean coverage | Mean abs corr |
| --- | ---: | ---: |
| size | 1.000 | 0.264 |
| value | 0.932 | 0.340 |
| lowvol | 0.895 | 0.156 |
| momentum | 0.790 | 0.492 |
| liquidity | 0.958 | 0.300 |

## Interpretation

- The H1 raw shape is not the problem for this repaired valuation composite.
- The signal is still dominated by style/industry exposure: max absolute style correlation is 0.953.
- After industry de-meaning and size/value/lowvol/momentum/liquidity controls, residual IC becomes significantly negative.
- This explains why direct TopN daily-basic candidates can show occasional raw IC structure but fail portfolio translation.

## Decision

Do not promote or parameter-tune daily-basic valuation repair. Do not run a portfolio grid for this family. The daily-basic line should either remain diagnostic-only or require a genuinely new orthogonal construction with preregistered residual controls.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download.
- No final-holdout tuning.
- Generated `data/reports` artifacts remain out of Git.
