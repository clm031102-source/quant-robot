# CN Stock PV Corr Reversal Costed Exclusion Round61

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Test whether the Round60 `formula_pv_corr_reversal_20` bottom-exclusion signal survives as a costed, capacity-aware portfolio risk filter.

## Inputs

- Config: `configs/experiment_grid_cn_stock_pv_corr_reversal_conversion_round60_20260621.json`
- Factor: `formula_pv_corr_reversal_20`
- Period: 2015-01-05 through 2025-12-31
- Bottom quantile excluded: 20%
- Holding period: 20
- Cost: 10 bps
- Market impact: 20 bps
- Max participation: 1%
- Min entry amount: 10,000,000
- Portfolio value: 1,000,000
- Target gross exposure: 1.0

## Results

### Rebalance 5

Output: `data/reports/bottom_exclusion_portfolio_pv_corr_reversal_round61_20260621_reb5_liquid10m`

- Classification: `research_lead_risk_filter`
- Total return: 111.83%
- Benchmark total return: 64.98%
- Relative return: 46.85%
- Gross total return: 175.89%
- Annualized return: 1.82%
- Sharpe: 0.2872
- Overlap-adjusted Sharpe: 0.1604
- Max drawdown: -56.52%
- Win rate: 48.14%
- Positive relative folds: 10 / 11
- Capacity-limited trades: 0

### Rebalance 10

Output: `data/reports/bottom_exclusion_portfolio_pv_corr_reversal_round61_20260621_reb10_liquid10m`

- Classification: `research_lead_risk_filter`
- Total return: 105.66%
- Benchmark total return: 55.12%
- Relative return: 50.54%
- Gross total return: 167.69%
- Annualized return: 1.08%
- Sharpe: 0.1722
- Overlap-adjusted Sharpe: 0.1297
- Max drawdown: -56.76%
- Win rate: 50.50%
- Positive relative folds: 11 / 11
- Capacity-limited trades: 0

## Interpretation

The bottom-exclusion translation works directionally. It improves the retained market basket after costs and liquidity filtering, and the relative-return fold stability is strong. The result is still not promotable because risk quality is too weak:

- overlap-adjusted Sharpe is far below the 0.5 costed candidate threshold;
- max drawdown breaches the 50% drawdown limit;
- annualized return is too low for the drawdown consumed;
- this is a broad market risk filter, not a capital-efficient standalone strategy.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- Costed risk-filter candidate: 0
- Research lead: 1

Next direction: run a constrained risk-overlay sensitivity on this same lead only.

Allowed next tests:

- target gross exposure 0.5 and 0.75;
- stricter market regime or drawdown guard;
- no new formula families;
- no window tuning;
- hibernate this lead if risk-overlay cannot lift overlap-adjusted Sharpe or reduce drawdown enough.
