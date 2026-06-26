# CN Stock PV Corr Reversal Exposure Sensitivity Round62

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Test whether lower target gross exposure can turn the Round61 `formula_pv_corr_reversal_20` bottom-exclusion research lead into a risk-quality candidate.

## Inputs

- Config: `configs/experiment_grid_cn_stock_pv_corr_reversal_conversion_round60_20260621.json`
- Factor: `formula_pv_corr_reversal_20`
- Bottom quantile excluded: 20%
- Rebalance interval: 10
- Holding period: 20
- Cost: 10 bps
- Market impact: 20 bps
- Max participation: 1%
- Min entry amount: 10,000,000
- Portfolio value: 1,000,000

## Results

### Target Gross Exposure 0.50

Output: `data/reports/bottom_exclusion_portfolio_pv_corr_reversal_round62_20260621_reb10_liquid10m_exposure0p5`

- Classification: `research_lead_risk_filter`
- Total return: 51.60%
- Benchmark total return: 32.02%
- Relative return: 19.58%
- Gross total return: 72.97%
- Annualized return: 0.62%
- Sharpe: 0.1722
- Overlap-adjusted Sharpe: 0.1297
- Max drawdown: -32.59%
- Win rate: 50.50%
- Positive relative folds: 11 / 11
- Capacity-limited trades: 0

### Target Gross Exposure 0.75

Output: `data/reports/bottom_exclusion_portfolio_pv_corr_reversal_round62_20260621_reb10_liquid10m_exposure0p75`

- Classification: `research_lead_risk_filter`
- Total return: 79.05%
- Benchmark total return: 45.22%
- Relative return: 33.83%
- Gross total return: 118.19%
- Annualized return: 0.87%
- Sharpe: 0.1722
- Overlap-adjusted Sharpe: 0.1297
- Max drawdown: -45.67%
- Win rate: 50.50%
- Positive relative folds: 11 / 11
- Capacity-limited trades: 0

## Interpretation

Reducing exposure reduces drawdown, but it does not improve the weak risk-adjusted return. The overlap-adjusted Sharpe is nearly unchanged at about 0.13, far below the 0.5 candidate threshold. This is expected because exposure scaling changes return and volatility together; it can make the strategy less dangerous, but it does not create a better edge.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- Costed risk-filter candidate: 0
- Research lead: 1

The lead should not be promoted. It can remain as a defensive overlay idea only if paired with a stronger return engine. If the next review does not identify a public-method-backed way to improve risk-adjusted return, hibernate this line and rotate to another family.
