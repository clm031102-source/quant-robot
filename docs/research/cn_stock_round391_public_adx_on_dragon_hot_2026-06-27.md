# CN Stock Round391 - Public ADX On Dragon-Hot Projection

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round391 tested whether public technical indicators should be used as direct alpha families or only as selected-entry defensive filters.

The test projected public-factor cash filters onto the frozen official Dragon-Tiger hot-chase event template, then reused the validated Round384 vol-target and ZZ500 wrapper.

## New Tooling

- `src/quant_robot/ops/shortlist_public_factor_entry_filter.py`
- `scripts/run_shortlist_public_factor_entry_filter.py`
- `src/quant_robot/ops/shortlist_event_return_wrapper.py`
- `scripts/run_shortlist_event_return_wrapper.py`
- `tests/unit/test_shortlist_public_factor_entry_filter.py`
- `tests/unit/test_shortlist_event_return_wrapper.py`

The wrapper now supports `--reuse-reference-vol-target-exposure`, which reproduced the Round384 event stream to numerical precision before applying new candidate returns.

## Output

- Projection: `data/reports/round391_24h_profit_sprint_public_factor_on_dragon_hot_projection_20260627`
- Wrapped events: `data/reports/round391_24h_profit_sprint_adx_on_dragon_hot_vt6_zz500_projection_20260627`
- OOS: `data/reports/round391_24h_profit_sprint_adx_on_dragon_hot_oos_20260627`
- Block audit: `data/reports/round391_24h_profit_sprint_adx_on_dragon_hot_block_audit_20260627`
- Beta audit: `data/reports/round391_24h_profit_sprint_adx_on_dragon_hot_beta_audit_20260627`

## Key Result

Only `adx_trend_strength_exhaustion_reversal_14_20:bottom20` deserved continuation.

Official-template projection vs Dragon-Hot base:

| Candidate | Ann | Total | Overlap Sharpe | Max DD | Missing Factor Share | Blockers |
|---|---:|---:|---:|---:|---:|---|
| Dragon-Hot base | 5.94% | 1.5979 | 0.4541 | -32.87% | n/a | none |
| ADX bottom20 | 6.08% | 1.6574 | 0.5174 | -25.85% | 47.06% | missing coverage, unmatched contribution |

Wrapped with Round384 vol-target and ZZ500 regime exposure:

| Candidate | Ann | Total | Sharpe | Overlap Sharpe | Max DD | Leave-One-Year Min Ann |
|---|---:|---:|---:|---:|---:|---:|
| Dragon-Hot 100 | 6.45% | 1.8120 | 0.987 | 0.5324 | -28.57% | 3.96% |
| ADX-on-Dragon 100 | 6.44% | 1.8082 | 1.097 | 0.5936 | -24.12% | 4.31% |

OOS split:

| Candidate | Mean OOS Ann | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| Dragon-Hot 100 | 8.02% | 0.8693 | -23.68% | 90.0% |
| ADX-on-Dragon 100 | 8.04% | 0.9612 | -19.42% | 90.0% |

ZZ500 beta audit:

| Candidate | Beta | R2 | Hedged Ann | Hedged Overlap | Hedged DD |
|---|---:|---:|---:|---:|---:|
| Dragon-Hot 100 | 0.0396 | 0.2496 | 6.41% | 0.8429 | -13.28% |
| ADX-on-Dragon 100 | 0.0350 | 0.2443 | 6.40% | 0.9240 | -11.33% |

## Decision

Keep ADX as a defensive selected-entry research lead only.

Do not expand SuperTrend or smart-money as direct signals. In this projection they either had very high missing-factor share or did not improve the wrapped event stream enough to justify more parameter work.

## Process Lesson

Public indicators should enter this project as narrow state filters around a proven primary event lane, not as blind TopN alpha grids. Coverage parity must be repaired before any ADX-derived lane can move beyond observation status.
