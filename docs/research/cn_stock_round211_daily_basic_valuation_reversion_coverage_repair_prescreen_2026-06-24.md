# CN Stock Round211 Daily-Basic Valuation Reversion Coverage Repair Prescreen

- Date: 2026-06-24
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock daily-basic valuation coverage-repair candidate
- Safety: research-to-review only; no broker, no account reads, no orders, no live trading

## Objective

Round211 executes the only repair path allowed by Round210: replace the sparse `dv_ttm` leg in the Round132 valuation reversion factor with the coverage-clean `dv_ratio` leg.

This is not a parameter expansion. It is a preregistered field-coverage repair.

## Preregistered Candidate

Config:

```text
configs/daily_basic_candidate_specs_round211_valuation_reversion_coverage_repair_20260624.json
```

Formula:

```text
daily_basic_valuation_reversion_dvratio_quality_60 =
0.45*cs_z(-pb_z_60)+0.30*cs_z(-ps_ttm_z_60)+0.25*cs_z(dv_ratio)
```

Required fields:

```text
pb|ps_ttm|dv_ratio
```

Portfolio backtest allowed: false. Promotion allowed: false.

## Command

```powershell
python scripts\run_daily_basic_non_price_public_carry_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --candidate-spec-json configs\daily_basic_candidate_specs_round211_valuation_reversion_coverage_repair_20260624.json --output-dir data\reports\round211_daily_basic_valuation_reversion_coverage_repair_prescreen_20260624 --analysis-start-date 2023-07-03 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --min-cross-section 100 --min-ic-observations 80 --min-field-coverage-ratio 0.80 --min-field-coverage-clean-ratio 0.80 --min-capacity-clean-ratio 0.80 --min-signal-date-amount 10000000
```

## Data

- Bar rows: 3,251,232
- Daily-basic rows: 3,262,000
- Assets: 5,567
- Factor rows: 3,262,000
- Label rows: 6,352,627
- Aligned rows: 6,352,627
- Tests: 2
- Final holdout included: false

## Coverage Result

- Coverage-pass candidates: 1 / 1
- Required-field median coverage: 1.0000
- Required-field clean ratio: 0.9225
- Capacity clean ratio: 0.9585
- Min field coverage ratio: 0.3333
- Coverage decision: pass

The coverage repair worked mechanically. The old `dv_ttm` coverage blocker is removed.

## Prescreen Results

| Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Monotonicity | Top turnover | FDR | Lead | Blockers |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| 20 | 0.0677 | 0.526 | 12.72 | 67.2% | 0.0254 | 0.400 | 14.4% | yes | no | `quantile_monotonicity_weak` |
| 5 | 0.0588 | 0.453 | 11.09 | 69.2% | -0.0164 | -0.300 | 14.4% | yes | no | `top_minus_bottom_quantile_not_positive`, `quantile_monotonicity_weak` |

## Interpretation

The repaired factor has strong rank-IC evidence but fails the shape test.

Useful facts:

- h20 mean IC 0.0677 and ICIR 0.526 are strong for this project.
- h20 IC positive rate is 67.2%.
- the field-coverage blocker is gone.
- h20 Q5-Q1 is positive but small at 2.54%.

Blocking facts:

- h20 quantile monotonicity is only 0.400, below the research-lead gate.
- h5 Q5-Q1 is negative, so the short-horizon top bucket is not reliable.
- turnover is 14.4%, high enough that cost/capacity still matters.
- this is still a prescreen, not a portfolio validation.

## Decision

- Promotable factors: 0
- Paper-ready factors: 0
- Research leads by strict gate: 0
- Diagnostic leads: 1, because h20 IC/ICIR are strong after coverage repair
- Next action: run a shape and exposure audit before any portfolio grid

Round211 should not be promoted. It should not trigger TopN optimization yet.

The correct next step is:

```text
round212_daily_basic_valuation_reversion_shape_exposure_audit
```

That audit should explain whether the strong IC is coming from industry/style/value beta, middle-bucket ordering, microcap/capacity tails, or a non-monotonic payoff shape that cannot translate into a tradable long-only signal.
