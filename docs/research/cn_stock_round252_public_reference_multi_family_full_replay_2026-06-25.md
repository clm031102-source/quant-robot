# CN Stock Round252 Public Reference Multi-Family Full Replay

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round251 rejected share-unlock and pledge-supply event ranking after the yearly coverage gate. Round252 did not continue tuning that failed event family. Instead, it replayed the frozen Round127 public-reference multi-family candidate set on the full 2015-2025 research window to answer a specific question:

Can any already pre-registered public technical, Alpha101, qlib-style, smart-money, moneyflow, or composite family survive long-cycle IC, multiple-testing, and quantile-shape gates before portfolio testing?

This was a no-new-formula replay. The 2026 final holdout stayed blocked.

## Method

- Source preregistration: `docs/research/cn_stock_public_reference_multi_family_preregistration_round127_2026-06-22.md`
- Result packet: `data/reports/round252_public_reference_multi_family_full_2015_2025_20260625/public_reference_multi_family_prescreen.json`
- Candidate set: 20 frozen candidates across 9 families.
- Horizons: 5, 10, and 20 trading days.
- Execution lag: 1 trading day.
- Analysis window: 2015-01-01 through 2025-12-31.
- Minimum cross-section: 100 stocks.
- Minimum IC observations: 80.
- Final holdout: excluded.

Command:

```powershell
.venv\Scripts\python.exe scripts\run_public_reference_multi_family_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --factor-input-root data\processed --moneyflow-input-root data\processed --output-dir data\reports\round252_public_reference_multi_family_full_2015_2025_20260625 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 10 --horizon 20 --execution-lag 1 --min-cross-section 100 --min-ic-observations 80 --min-signal-date-amount 10000000
```

## Full-Sample Results

| Metric | Value |
|---|---:|
| Bar assets | 5,707 |
| Unique assets | 5,702 |
| Bar rows | 10,785,537 |
| Factor rows | 197,162,984 |
| Label rows | 32,140,060 |
| Aligned rows | 587,433,698 |
| Candidates | 20 |
| Families | 9 |
| Tests | 60 |
| FDR-significant tests | 56 |
| Research leads | 0 |
| Portfolio backtest allowed | 0 |
| Promotion allowed | 0 |

## Most Informative Rows

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Lead | Main blocker |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `alpha101_rank_pv_reversal_liquid_20` | 20 | 0.0468 | 0.479 | 24.61 | 68.1% | -0.0313 | -0.3 | no | quantile spread negative, weak monotonicity |
| `alpha101_rank_pv_reversal_liquid_20` | 5 | 0.0450 | 0.468 | 24.11 | 68.4% | 0.0009 | 0.4 | no | weak monotonicity |
| `main_force_divergence_reversal_5_20` | 5 | 0.0338 | 0.239 | 12.29 | 58.5% | 0.0034 | -0.1 | no | ICIR below gate, weak monotonicity |
| `residual_range_contraction_reversal_20` | 20 | 0.0251 | 0.187 | 9.60 | 57.6% | 0.0252 | 0.6 | no | ICIR below gate |
| `bollinger_bandwidth_reversal_liquid_20` | 20 | 0.0224 | 0.184 | 9.44 | 56.6% | 0.0328 | 0.5 | no | ICIR below gate, weak monotonicity |
| `donchian_breakout_efficiency_liquid_20` | 5 | -0.0684 | -0.510 | -26.21 | 29.3% | 0.0210 | 0.7 | no | wrong IC direction |
| `rsrs_slope_acceleration_quality_18_60` | 10 | -0.0444 | -0.525 | -26.94 | 28.9% | 0.0148 | 0.3 | no | wrong IC direction |

## Yearly Diagnostics

The replay is not a total absence of signal. It is mostly an IC-to-portfolio translation failure.

- `alpha101_rank_pv_reversal_liquid_20` at 20 days had positive mean IC in 10 of 11 calendar years. The only negative year was 2023. Its 2024-2025 mean IC was 0.0591. The blocker is not raw IC; it is that the top-minus-bottom quantile spread is negative and monotonicity is weak.
- The same Alpha101 candidate at 5 days had positive mean IC in all 11 years and 2024-2025 mean IC of 0.0612, but its Q5-Q1 spread was only 0.0009 and monotonicity was still weak.
- `main_force_divergence_reversal_5_20` at 5 days also had positive mean IC in all 11 years and 2024-2025 mean IC of 0.0503, but ICIR was only 0.239 and quantile monotonicity was negative.
- `donchian_breakout_efficiency_liquid_20` and `rsrs_slope_acceleration_quality_18_60` were consistently negative across all 11 years. These are useful diagnostics, but reversing the sign is not allowed without a fresh preregistered inverse hypothesis.

## Interpretation

Round252 rejects direct promotion and rejects portfolio-grid escalation.

The main lesson is precise: long-cycle, full-window replay finds statistically significant rank relationships, but the best rows do not become clean long-only ranking factors. High t-stat and stable positive IC are insufficient when the quantile spread, monotonicity, or intended direction fails. Running TopN grids on these rows would repeat the old IC-only promotion error.

This also closes one process gap. The earlier Round128 public-reference run ended in 2023-07-31 and showed apparent research leads. Extending the same frozen candidate set to 2025-12-31 removes lead status. The added 2024-2025 evidence does not rescue the family because the shape problem remains.

## Decision

- Promotable factors from Round252: 0.
- Research leads from Round252: 0.
- Portfolio backtest allowed candidates: 0.
- Direct public-reference multi-family replay is hibernated as a promotion path.
- `alpha101_rank_pv_reversal_liquid_20` and `main_force_divergence_reversal_5_20` are blocked from direct portfolio grids after their quantile-shape failure.
- Negative Donchian and RSRS diagnostics are recorded, but inverse-direction mining requires a new preregistration and cannot be treated as a free sign flip.

## Next Direction

Round253 should rotate away from direct public technical, public Alpha101, and moneyflow divergence portfolio grids. The next allowed direction is:

`round253_rotate_to_non_price_volume_expectation_revision_or_industry_relative_surprise`

Required before Round253:

- Read this report.
- Confirm Round252 produced zero research leads.
- Confirm no portfolio grid for `alpha101_rank_pv_reversal_liquid_20` or `main_force_divergence_reversal_5_20`.
- Keep 2026 final holdout blocked.
- Use a fresh economic hypothesis, preferably non-price-volume expectation revision or industry-relative surprise, before generating candidates.
