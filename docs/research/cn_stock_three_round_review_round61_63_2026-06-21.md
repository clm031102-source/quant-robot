# CN Stock Three-Round Review Round61-63

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Rounds Reviewed

Round61: costed bottom-exclusion portfolio.

- Best rebalance 5 total return: 111.83%
- Best rebalance 5 relative return: 46.85%
- Best rebalance 5 overlap-adjusted Sharpe: 0.1604
- Best rebalance 5 max drawdown: -56.52%
- Best rebalance 10 total return: 105.66%
- Best rebalance 10 relative return: 50.54%
- Best rebalance 10 overlap-adjusted Sharpe: 0.1297
- Best rebalance 10 max drawdown: -56.76%
- Capacity-limited trades: 0

Round62: exposure sensitivity.

- Exposure 0.50 total return: 51.60%
- Exposure 0.50 relative return: 19.58%
- Exposure 0.50 max drawdown: -32.59%
- Exposure 0.50 overlap-adjusted Sharpe: 0.1297
- Exposure 0.75 total return: 79.05%
- Exposure 0.75 relative return: 33.83%
- Exposure 0.75 max drawdown: -45.67%
- Exposure 0.75 overlap-adjusted Sharpe: 0.1297

Round63: public reference review.

- Qlib, Alphalens, vectorbt, pyfolio, WorldQuant 101, and MLFinLab-style overfitting lessons were checked.
- The line fails the public-method standard for standalone continuation because risk-adjusted return is too weak.

## Conclusion

`formula_pv_corr_reversal_20` is useful information, but not a standalone profitable factor. It is a defensive exclusion overlay: it can improve a broad retained basket, but it does not create enough risk-adjusted return after costs.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- Costed risk-filter candidate: 0
- Research lead to keep in reserve: 1
- Active line status: hibernated as standalone

## Direction Adjustment

Next direction: `daily_basic_quality_value_lowvol_public_method_batch`.

Why:

- The project needs a stronger return engine, not more pv-corr risk filtering.
- Tushare daily-basic data has already been purchased and should be used for CN stock value/quality/liquidity signals.
- Public methods point toward interpretable factor families with neutralization, quantile spreads, turnover, and portfolio risk attribution.

Required first batch:

- small number of pre-registered daily-basic composite factors;
- value plus quality plus low-volatility/liquidity-capacity controls;
- industry and size neutral IC before portfolio expansion;
- costed portfolio conversion only after neutral IC and quantile spread survive;
- no broad parameter sweep.
