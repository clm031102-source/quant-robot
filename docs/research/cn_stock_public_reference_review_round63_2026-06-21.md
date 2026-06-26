# CN Stock Public Reference Review Round63

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Compare the current `formula_pv_corr_reversal_20` bottom-exclusion line with public quant research workflows before spending more compute on it.

## Public References Checked

- Qlib: https://github.com/microsoft/qlib
- Alphalens: https://github.com/quantopian/alphalens
- vectorbt: https://github.com/polakowo/vectorbt and https://vectorbt.dev/
- pyfolio: https://github.com/quantopian/pyfolio
- WorldQuant 101 formulaic alphas paper: https://arxiv.org/pdf/1601.00991
- MLFinLab / backtest-overfitting concepts: https://github.com/hudson-and-thames/mlfinlab

## Method Lessons

Qlib lesson:

- Treat factor work as an end-to-end research workflow, not isolated indicator hunting.
- Keep data, model, evaluation, and portfolio construction connected.

Alphalens lesson:

- Strong factors need quantile returns, IC, turnover, and group/sector diagnostics.
- A factor with IC but poor quantile portfolio conversion is not done.

vectorbt lesson:

- Batch experimentation is useful only when the parameter surface is pre-registered and cheap.
- Scaling broad grids after a rejected hypothesis is wasteful.

pyfolio lesson:

- Portfolio-level risk, drawdown, exposure, and attribution matter more than single-factor IC.
- A weak Sharpe strategy that only improves relative return is not sufficient.

WorldQuant 101 lesson:

- Public formula alphas are hypothesis templates, not plug-and-play profit engines.
- Formula alphas typically require neutralization, decay, turnover control, and combination.

MLFinLab / overfitting lesson:

- After many trials, the project needs multiple-testing discipline, purged/walk-forward validation, and conservative Sharpe haircuts before believing any result.

## Audit Against Current Lead

Current lead: `formula_pv_corr_reversal_20` as a bottom-exclusion risk filter.

What passes:

- long-cycle IC survives;
- industry-neutral IC survives;
- bottom bucket persistently drags returns;
- costed exclusion portfolio improves relative return;
- capacity is clean after 10m liquidity floor.

What fails:

- overlap-adjusted Sharpe stays near 0.13-0.16;
- full exposure drawdown is about -56%;
- exposure scaling lowers drawdown but does not improve risk-adjusted return;
- direct buy-signal version was rejected;
- this line does not supply a strong return engine by itself.

## Decision

Hibernate `pv_corr_reversal_20` as a standalone mining line.

Keep it only as a possible defensive overlay for a future stronger long book. Do not spend more rounds tuning it alone.

## Next Direction

Rotate to a public-method-backed quality/value/low-volatility composite family using Tushare daily-basic plus price-volume controls.

Required design:

- industry and size neutral IC;
- Alphalens-style quantile spread and turnover diagnostics;
- pyfolio-style portfolio risk and drawdown gates;
- no broad parameter sweep before the first conversion audit;
- factor candidates must be economically interpretable: value, quality, low volatility, liquidity capacity.
