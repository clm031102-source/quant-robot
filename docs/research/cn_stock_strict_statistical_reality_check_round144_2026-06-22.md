# CN Stock Strict Statistical Reality Check - Round144

## Scope

Round144 added a reusable statistical reality-check layer for CN stock factor-mining leaderboards. This is a research-to-review gate only; it does not permit broker connectivity, live account reads, order placement, or automatic live trading.

## What Was Implemented

- `src/quant_robot/ops/factor_statistical_reality_check.py`
- `scripts/run_factor_statistical_reality_check.py`
- Unit coverage for:
  - Probabilistic Sharpe and conservative Deflated Sharpe approximation.
  - Benjamini-Hochberg FDR accounting.
  - Purged CPCV split planning with optional embargo.
  - Parameter sensitivity heatmap around the best cell.
  - CLI artifact generation.

## Quality Gate Impact

The CN stock factor-mining quality gate now records executable evidence for all strict-statistics controls:

- `deflated_sharpe`: implemented.
- `cpcv_purged_cross_validation`: implemented.
- `white_reality_check_or_fdr`: implemented via FDR; full White Reality Check bootstrap remains a future enhancement.
- `parameter_sensitivity_heatmap`: implemented.

Latest gate summary:

- Total controls: 32
- Implemented: 8
- Partial: 11
- Planned: 13
- Missing: 0
- Startup gate: cleared
- Promotion gate: blocked

Promotion remains blocked because tradeability, PIT financial timing, portfolio construction, China regime, and event-factor controls are still not fully implemented.

## Reality-Check Samples

### Round126 Turnover Repair Champion Conversion

Input:

- `data/reports/turnover_repair_champion_portfolio_conversion_round126_20260622/turnover_repair_champion_portfolio_conversion_leaderboard.csv`

Command:

```powershell
python scripts\run_factor_statistical_reality_check.py --experiments-path data\reports\turnover_repair_champion_portfolio_conversion_round126_20260622\turnover_repair_champion_portfolio_conversion_leaderboard.csv --output-dir data\reports\factor_statistical_reality_check_round144_turnover_repair --metric-column overlap_autocorr_adjusted_sharpe --observations-column overlap_effective_sample_size --x-param cost_bps --y-param portfolio_value --sensitivity-metric overlap_autocorr_adjusted_sharpe --min-deflated-sharpe-probability 0.95
```

Result:

- Rows / hypotheses: 12 / 12
- Best overlap-adjusted Sharpe: 0.2258
- Max DSR probability: 0.9796
- DSR pass count: 12
- FDR significant count: 12
- Statistical candidate count: 12
- Sensitivity stable peak: true
- Promotion allowed by this report: false

Interpretation:

This is an important negative lesson. Round126 can look statistically significant because it has many observations, but it is still not promotable. The earlier rejection remains valid because the portfolio evidence has severe drawdown, extreme trade contamination, calendar-holding constraints, and low absolute overlap Sharpe. Strict statistics are necessary but not sufficient.

### Round141 Clean Walk-Forward Leaderboard

Input:

- `data/reports/daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_round141_20260622/daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_leaderboard.csv`

Result:

- Rows / hypotheses: 6 / 6
- Best overlap-adjusted Sharpe: 3.3277
- Max DSR probability: 1.0
- DSR pass count: 6
- FDR significant count: 6
- Statistical candidate count: 6
- Sensitivity stable peak: true
- Promotion allowed by this report: false

Interpretation:

Round141 remains a stronger research lead than Round126, but the statistic is derived from Sharpe rather than an independent return bootstrap or White Reality Check. It may proceed to the next audit layer, not to promotion.

### Round141 Fold-Level CPCV Smoke

Input:

- `data/reports/daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_round141_20260622/daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_folds.csv`

Result:

- Rows: 18
- Unique case hypotheses: 6
- CPCV splits: 3
- Embargo observations requested: 1
- DSR pass count: 18
- FDR significant count: 18

Interpretation:

The CPCV planner is now executable on fold-level date columns. This smoke does not replace a full purged CPCV backtest; it proves the split accounting and artifact path are available for future mining and validation runs.

## Operational Rule Going Forward

Before a factor can be treated as a serious candidate, its leaderboard should pass:

1. Long-cycle same-parameter replay.
2. Tradeability gate.
3. Cost/capacity/turnover gate.
4. Strict-statistics reality check from this round.
5. Parameter sensitivity heatmap.
6. Regime coverage.
7. Event-factor contamination audit.
8. Final holdout or paper gate.

Passing Round144 alone only means "continue auditing"; it never means "promote".

## Verification

```powershell
python -m unittest tests.unit.test_factor_statistical_reality_check tests.unit.test_factor_statistical_reality_check_cli tests.unit.test_factor_mining_quality_gate tests.unit.test_factor_mining_quality_gate_cli
python -m py_compile src\quant_robot\ops\factor_statistical_reality_check.py scripts\run_factor_statistical_reality_check.py
python scripts\run_factor_mining_quality_gate.py --config configs\factor_mining_quality_gate_cn_stock.json --output-dir data\reports\factor_mining_quality_gate_round144
python scripts\run_factor_mining_startup_gate.py --config configs\factor_mining_startup_cn_stock.json --output-dir data\reports\factor_mining_startup_gate_round144 --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start
```
