# CN Stock Industry-Neutral IC Audit Round 48 - 2026-06-21

## Purpose

Round48 audited the strongest CN stock public price-volume formula family from Round12. The question was not "can we add more parameters?", but:

- Is the strong RankIC only an industry exposure effect?
- Does the signal still work inside industries?
- Should the next step be raw TopN, industry-neutral portfolio construction, bottom-quantile exclusion, or stock-to-industry/ETF bridging?

## Added Tooling

New reusable audit module:

- `src/quant_robot/ops/industry_neutral_ic_audit.py`

New CLI:

- `scripts/run_industry_neutral_ic_audit.py`

New tests:

- `tests/unit/test_industry_neutral_ic_audit.py`

The tool compares:

- overall cross-sectional RankIC,
- within-industry RankIC,
- industry-mean RankIC,
- neutral retention ratio,
- classification into `industry_neutral_signal`, `industry_exposure_dominated`, `industry_mix_or_translation_unknown`, or `weak_or_unproven_signal`.

## Real Audit Run

Command:

```powershell
python scripts\run_industry_neutral_ic_audit.py `
  --grid-config configs\experiment_grid_cn_stock_public_formula_price_volume_fast_20260621.json `
  --source authority-processed-bars `
  --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --stock-basic data\processed\cn_stock_metadata `
  --output-dir data\reports\industry_neutral_ic_audit_public_formula_round48_20260621
```

Inputs:

- Factor family: public formula price-volume
- Factors: 3
- Horizon: 20 trading days
- Execution lag: 1 trading day
- Date-factor rows: 7,938
- Merged factor/label rows: 24,952,335
- Missing industry rows after valid factor/return filtering: 467,088

## Results

| Factor | Classification | Dates | Overall RankIC | Overall t | Industry-neutral RankIC | Neutral t | Industry RankIC | Industry t | Retention |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `formula_pv_corr_reversal_20` | `industry_neutral_signal` | 2646 | 0.0770 | 32.06 | 0.0879 | 49.86 | 0.0600 | 15.05 | 1.14 |
| `formula_volume_contraction_reversal_20` | `industry_neutral_signal` | 2646 | 0.0844 | 31.68 | 0.0910 | 49.41 | 0.0696 | 16.65 | 1.08 |
| `formula_range_contraction_breakout_20` | `industry_neutral_signal` | 2646 | 0.0639 | 16.52 | 0.0787 | 28.84 | 0.0243 | 4.79 | 1.23 |

Summary:

- Industry-neutral signal factors: 3
- Industry-exposure dominated factors: 0
- Weak/unproven factors: 0
- Recommended next actions: `run_industry_neutral_portfolio_backtest`, `repair_industry_metadata_coverage`

## Interpretation

This is an important correction to the prior diagnosis.

The public price-volume formula family is not merely an industry beta signal. All three factors retain strong RankIC inside industries, and the industry-neutral RankIC is stronger than the raw overall RankIC.

That means the failure of Round12 raw long-only TopN portfolios is more likely a portfolio-construction / translation problem:

- naive market-wide TopN may overconcentrate in bad microstructure pockets,
- the signal may work better as industry-neutral ranking,
- bottom-quantile exclusion may be more tradable than buying the top quantile alone,
- capacity and turnover gates still need to be respected,
- the industry metadata gap should be reduced before promotion-grade claims.

## Process Change

Before extending any CN stock factor family that has strong IC but rejected long-only portfolio results, run both:

```powershell
python scripts\run_ic_portfolio_gap_audit.py --leaderboard <leaderboard.csv> --output-dir <audit-output-dir>
```

```powershell
python scripts\run_industry_neutral_ic_audit.py --grid-config <experiment-grid.json> --stock-basic data\processed\cn_stock_metadata --output-dir <audit-output-dir>
```

If IC survives within industry, the next experiment must be an industry-neutral portfolio or exclusion overlay. Do not continue raw TopN parameter sweeps.

If IC disappears within industry, stop stock TopN work and translate the signal into industry breadth, risk state, or ETF/theme bridge logic.

## Next Direction

Round49 should test the public formula family with an industry-neutral portfolio construction layer:

- rank within industry first,
- avoid market-wide sector concentration,
- keep cost, capacity, turnover, and drawdown gates on,
- include bottom-quantile exclusion as a separate overlay,
- do not tune formula parameters after reading the Round48 audit.

Current promotable profitable factors: 0.

Current useful research lead: industry-neutral translation of public price-volume formula signals.
