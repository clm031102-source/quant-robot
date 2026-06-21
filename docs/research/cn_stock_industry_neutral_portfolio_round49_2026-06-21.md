# CN Stock Industry-Neutral Portfolio Round 49 - 2026-06-21

## Purpose

Round48 showed that the public price-volume formula family keeps strong RankIC inside industries. Round49 tested whether that signal can become a tradable long-only portfolio by changing only the portfolio construction layer:

- same factor family as Round12,
- same broad parameters as Round12,
- no formula tuning after reading Round48,
- selection changed from raw market-wide TopN to `industry_neutral_top_n`.

## Added Tooling

Reusable selection layer:

- `src/quant_robot/backtest/portfolio.py`
  - added `select_industry_neutral_top_n`
- `src/quant_robot/backtest/engine.py`
  - added `selection_method`
- `src/quant_robot/research/pipeline.py`
  - passes `selection_method` through the pipeline

New runner:

- `scripts/run_industry_neutral_portfolio_backtest.py`

New config:

- `configs/experiment_grid_cn_stock_public_formula_price_volume_industry_neutral_round49_20260621.json`

Tests:

- `tests/unit/test_backtest.py`
- `tests/unit/test_research_pipeline.py`

## Experiment

Command:

```powershell
python scripts\run_industry_neutral_portfolio_backtest.py `
  --config configs\experiment_grid_cn_stock_public_formula_price_volume_industry_neutral_round49_20260621.json `
  --source authority-processed-bars `
  --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --stock-basic data\processed\cn_stock_metadata `
  --output-dir data\reports\industry_neutral_portfolio_public_formula_round49_20260621
```

Selection rule:

- Within each signal date / market / factor, rank stocks inside each industry.
- Select first-ranked names across industries before second-ranked names.
- Equal weight selected names.
- Keep cost, capacity, regime, drawdown, `min_total_return`, and relative-return gates enabled.

## Results

Summary:

- Cases: 12
- Approved: 0
- Rejected: 12
- Capacity-limited cases: 7
- Best total return: 35.48%
- Best overlap-adjusted Sharpe: 0.1814
- Best relative return: -23.3827

Top cases:

| Rank | Factor | TopN | Rebalance | Total | Relative | Sharpe | Overlap Sharpe | Max DD | Win | Capacity-limited |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `formula_pv_corr_reversal_20` | 50 | 5 | 30.72% | -2343.03% | 0.3216 | 0.1814 | -26.12% | 46.73% | 0 |
| 2 | `formula_pv_corr_reversal_20` | 100 | 5 | 35.48% | -2338.27% | 0.3134 | 0.1771 | -26.71% | 46.87% | 0 |
| 3 | `formula_pv_corr_reversal_20` | 100 | 10 | 12.82% | -2360.93% | 0.1243 | 0.0994 | -32.48% | 48.06% | 0 |
| 4 | `formula_pv_corr_reversal_20` | 50 | 10 | 7.41% | -2366.34% | 0.1088 | 0.0918 | -30.81% | 48.69% | 0 |
| 5 | `formula_volume_contraction_reversal_20` | 100 | 5 | 11.85% | -2361.90% | 0.1396 | 0.0857 | -35.03% | 48.24% | 1 |

## Interpretation

Industry-neutral construction improves the best `pv_corr_reversal` rows versus the weakest raw long-only behavior, and the best two rows are capacity-clean at a 1M portfolio value.

But this is still not a usable profitable factor:

- all 12 cases are rejected,
- every case fails relative return,
- overlap-adjusted Sharpe is far too low,
- win rate stays below 50%,
- drawdowns remain large,
- `volume_contraction` and `range_contraction` remain capacity or return blocked,
- tail RankIC is mixed; the best Top50 row has negative tail RankIC.

The useful conclusion is not "promote industry-neutral public formulas." The useful conclusion is narrower:

`formula_pv_corr_reversal_20` may contain an exclusion/risk signal, but the long-only buy-list translation is still weak.

## Decision

Do not promote any Round49 case.

Do not continue raw TopN expansion for this family.

If this family is revisited after the Round50 sync, the only justified next test is a benchmark-aware bottom-quantile exclusion or risk-overlay experiment:

- avoid bottom-ranked names rather than buy top-ranked names,
- compare against a broad equal-weight or benchmark-like basket,
- keep capacity and turnover gates,
- do not tune formula parameters.

Current promotable profitable factors: 0.

Current research lead: weak exclusion/risk-control candidate only, not a buy-list factor.
