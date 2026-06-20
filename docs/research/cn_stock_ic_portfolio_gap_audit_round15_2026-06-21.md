# CN Stock IC-to-Portfolio Gap Audit Round 15

Date: 2026-06-21

## Purpose

Round 15 added a repeatable audit tool for the current bottleneck: strong cross-sectional IC does not automatically become a profitable long-only portfolio.

The goal is to stop wasting rounds on formula tweaks when the evidence says the signal is mostly an exclusion, short, capacity, or portfolio-construction problem.

## Added Tooling

New module:

- `src/quant_robot/ops/ic_portfolio_gap_audit.py`

New CLI:

- `scripts/run_ic_portfolio_gap_audit.py`

New tests:

- `tests/unit/test_ic_portfolio_gap_audit.py`

The tool reads experiment leaderboards and classifies cases by:

- strong RankIC evidence,
- long-only translation gap,
- exclusion-signal candidate,
- capacity blockage,
- extreme trade contamination,
- promotable long-only status.

It also emits recommended next actions such as bottom-quantile exclusion, ETF/theme breadth translation, beta/sector/size diagnostics, and capacity filters.

## Validation

Targeted tests:

- `python -m unittest tests.unit.test_ic_portfolio_gap_audit`
- `python -m unittest tests.unit.test_ic_portfolio_gap_audit tests.unit.test_long_cycle_replay`

Both passed.

## Applied Evidence

### Round 12 Public Formula Audit

Input:

- `data/reports/experiment_grid_cn_stock_public_formula_price_volume_fast_20260621_clean/leaderboard.csv`

Output:

- `data/reports/ic_portfolio_gap_audit_public_formula_round12_20260621`

Summary:

- Cases: 12
- Strong RankIC cases: 12
- IC-to-portfolio gap cases: 12
- Exclusion signal cases: 12
- Capacity-limited cases: 8
- Promotable long-only cases: 0

Recommended next actions:

- `bottom_quantile_exclusion_overlay`
- `stock_to_etf_breadth_bridge`
- `beta_sector_size_diagnostic`
- `stop_raw_formula_topn_sweeps`
- `capacity_filter_or_liquidity_gate`

### Round 14 Momentum Confirmation Audit

Input:

- `data/reports/experiment_grid_cn_stock_public_formula_price_volume_momentum_confirmed_fast_20260621_clean/leaderboard.csv`

Output:

- `data/reports/ic_portfolio_gap_audit_public_formula_momentum_round14_20260621`

Summary:

- Cases: 8
- Strong RankIC cases: 8
- IC-to-portfolio gap cases: 8
- Exclusion signal cases: 8
- Capacity-limited cases: 8
- Promotable long-only cases: 0

## Interpretation

This confirms the Round 13 and Round 14 diagnosis:

- The formula family has real rank information.
- The signal is not yet a profitable long-only buy list.
- Adding momentum confirmation made capacity worse.
- The best current use is likely exclusion, ETF/theme breadth, or portfolio risk control.

## Process Change

Before continuing a factor family after a strong IC but rejected long-only result, run:

```powershell
python scripts\run_ic_portfolio_gap_audit.py --leaderboard <leaderboard.csv> --output-dir <audit-output-dir>
```

If the audit returns `stop_raw_formula_topn_sweeps`, do not continue parameter sweeps for that family until a portfolio translation layer has been tested.

## Current Conclusion

Round 15 produced 0 new factors and 0 promotable factors.

It produced a reusable efficiency guardrail. The next factor work should implement and test the first translation layer, starting with bottom-quantile exclusion or ETF/theme breadth, rather than inventing more raw formula variants.
