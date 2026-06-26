# CN Stock Round212 Daily-Basic Valuation Shape/Exposure Audit

- Date: 2026-06-24
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock daily-basic valuation repaired candidate audit
- Safety: research-to-review only; no broker, no account reads, no orders, no live trading

## Objective

Round212 audits the only diagnostic lead from Round211:

```text
daily_basic_valuation_reversion_dvratio_quality_60
```

Round211 showed strong h20 rank IC after field-coverage repair, but failed quantile monotonicity. Round212 asks whether the signal survives:

- quantile shape inspection;
- industry exposure;
- size/value/lowvol/momentum/liquidity style controls;
- lightweight residual IC after industry de-meaning and style regression.

## Command

```powershell
python scripts\run_daily_basic_valuation_shape_exposure_audit.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --stock-basic data\reports\round212_stock_basic_snapshot_20260624\metadata\tushare_stock_basic\list_status=L\snapshot=2026-06-24\part-00000.parquet --output-dir data\reports\round212_daily_basic_valuation_shape_exposure_audit_20260624 --analysis-start-date 2023-07-03 --analysis-end-date 2025-12-31 --horizons 20 --execution-lag 1 --min-dates 80 --min-cross-section 100
```

## Data

- Bar rows: 3,251,232
- Daily-basic rows: 3,262,000
- Factor rows: 3,262,000
- Label rows: 3,134,755
- Style-factor rows: 3,262,000 wide rows
- Stock-basic rows: 5,528
- Horizon: 20
- Final holdout included: false

## Shape Result

| Horizon | q1 | q2 | q3 | q4 | q5 | q5-q1 | Mono | Best bucket | Shape pass |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 20 | 0.2188 | 0.3449 | 0.4301 | 0.4867 | 0.2442 | 0.0254 | 0.400 | q4 | no |

Shape blockers:

- `top_quantile_not_best_bucket`
- `quantile_monotonicity_weak`

Interpretation: the signal ranks the worst bucket reasonably, but the best payoff is in q4, not q5. The extreme top bucket falls back toward q1, so raw TopN conversion is structurally unsafe.

## Exposure Result

| Metric | Value |
|---|---:|
| Raw h20 rank IC | 0.0677 |
| Raw IC t-stat | 12.72 |
| Raw IC positive rate | 67.2% |
| Residual h20 rank IC | 0.0002 |
| Residual IC t-stat | 0.08 |
| Residual positive rate | 51.9% |
| Residual retention | 0.003 |
| Max absolute style correlation | 0.929 |
| Mean industry R2 | 0.154 |
| Style coverage ratio | 0.892 |
| Missing industry fraction | 0.0107 |

Exposure classification:

```text
style_or_industry_exposure_dominated
```

Exposure blockers:

- `residual_ic_gate_failed`
- `style_coverage_below_threshold`

Style coverage details:

| Style | Mean coverage | Mean abs corr |
|---|---:|---:|
| size | 1.000 | 0.157 |
| value | 0.923 | 0.346 |
| lowvol | 0.982 | 0.322 |
| momentum | 0.964 | 0.608 |
| liquidity | 0.993 | 0.181 |

The style-coverage blocker is partly caused by early rolling-window style gaps, but this is not the main rejection reason. The main rejection is residual IC collapse.

## Decision

- Promotable factors: 0
- Paper-ready factors: 0
- Strict research leads: 0
- Diagnostic leads after audit: 0
- Portfolio grid allowed: false
- Promotion allowed: false

The repaired daily-basic valuation reversion factor should be hibernated as a standalone alpha direction.

## Reason

The h20 IC looked strong before exposure control, but after industry de-meaning and size/value/lowvol/momentum/liquidity residualization, the signal disappears:

```text
raw IC 0.0677 -> residual IC 0.0002
```

That is not a drawdown-tolerance issue. It is an alpha-identity issue. The signal is mostly explainable by common style/valuation structure and does not currently translate into a clean long-only ranking factor.

## Next Direction

Rotate away from standalone daily-basic valuation reversion.

Valid next work:

```text
round213_new_family_rotation_after_valuation_reversion_hibernation
```

Round213 should use a genuinely different information source or structure, not another valuation-weight tweak. Preferred directions:

- public technical trend-state indicators with explicit regime and drawdown controls;
- smart-money or flow signals only if they are combined with residual/exposure controls from the start;
- event or macro/liquidity signals with point-in-time availability and no TopN grid until IC/shape gates pass.
