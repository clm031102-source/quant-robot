# CN Stock Portfolio Construction Policy Gate Round201

Date: 2026-06-23

## Objective

Round201 closes the portfolio-construction gap before direct factor mining resumes.

This round does not mine or promote factors. It creates a reusable policy gate so future portfolio grids cannot interpret raw TopN results without risk budget, volatility, industry, turnover, drawdown, and metric-pack constraints.

## Implemented Tool

Added:

- `src/quant_robot/ops/portfolio_construction_policy_gate.py`
- `scripts/run_portfolio_construction_policy_gate.py`
- `configs/portfolio_construction_policy_cn_stock.json`
- `tests/unit/test_portfolio_construction_policy_gate.py`
- `tests/unit/test_portfolio_construction_policy_gate_cli.py`

## Policy Parameters

Default CN stock policy:

- Max single-name weight: 5%
- Max position ADV participation: 1%
- Max gross exposure: 1.0
- Volatility targeting: enabled
- Target annual volatility: 15%
- Max annual volatility: 25%
- Volatility lookback: 60 days
- Max industry weight: 25%
- Max benchmark-relative industry deviation: 10%
- Minimum industry count: 5
- Max one-way turnover per rebalance: 35%
- Max annual turnover: 6.0
- Max cost degradation: 35%
- Rebalance churn limit: 50%
- Max drawdown soft tolerance: 30%
- De-risk drawdown threshold: 30%
- Hard-stop drawdown threshold: 45%
- Capacity and tradeability gates remain hard: true

Required metric pack:

- `total_return`
- `annual_return`
- `sharpe`
- `cost_adjusted_sharpe`
- `max_drawdown`
- `win_rate`
- `turnover`
- `capacity_usage`

## Real Policy Gate Run

Command:

```powershell
python scripts\run_portfolio_construction_policy_gate.py --config configs\portfolio_construction_policy_cn_stock.json --output-dir data\reports\round201_portfolio_construction_policy_gate_20260623
```

Result:

- Passes: true
- Missing controls: none
- Invalid policy items: none
- Missing metrics: none
- Implemented controls:
  - `risk_budget_position_sizing`
  - `volatility_targeting`
  - `industry_weight_constraints`
  - `turnover_constraints`
  - `stop_loss_or_de_risk_rules`

## Decision

Portfolio construction policy is now implemented as a pre-promotion gate.

This still does not make any historical factor profitable. It means future portfolio conversion must explicitly report the policy constraints and metric pack before results can be compared or promoted.

## Config Updates

Updated:

- `configs/factor_mining_quality_gate_cn_stock.json`
- `configs/factor_mining_startup_cn_stock.json`
- `src/quant_robot/ops/factor_mining_startup.py`

The startup protocol now requires:

- `portfolio_construction_policy_gate_before_portfolio_grid`
- `portfolio_required_metric_pack_before_promotion`
- `portfolio_risk_budget_constraints_required`
- `portfolio_drawdown_derisk_policy_required`
- `portfolio_construction_policy_gate_confirmed`
- `portfolio_grid_without_policy_gate_rejected`
- `portfolio_required_metric_pack_confirmed`
- `portfolio_drawdown_tolerance_not_capacity_waiver_confirmed`

## Next Action

Wire this policy gate into every future portfolio conversion output. A result packet that omits risk budget, volatility target, industry exposure, turnover/cost degradation, drawdown/de-risk status, or the full metric pack must be rejected before promotion review.
