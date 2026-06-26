# CN Stock Factor Mining Rounds 1-3 Audit

- Date: 2026-06-21
- Machine: office_desktop
- Task: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Review cadence: required after every 3 rounds
- Scope: CN A-share stock cross-sectional alpha, not ETF rotation

## Executive Decision

The first 3-round cycle found 8 public technical candidates and 0 promotable factors.

The useful conclusion is negative but valuable: public technical mean-reversion should not remain the primary standalone mining direction. It has visible IC, but the signal does not survive portfolio-level gates: tail IC, drawdown, relative return, extreme trade returns, and capacity controls.

Next direction: rotate away from standalone public technical factors. Use public technical indicators only as secondary components or gates inside a different family, preferably daily-basic value/quality/liquidity or residualized composite factors.

## Candidate Count

| round | family | candidates | promotable | research leads | main outcome |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | `public_technical` | 4 | 0 | 2 | RSI/Bollinger had IC, but drawdown/capacity/tail risk failed |
| 2 | `public_technical_liquidity` | 2 | 0 | 0 | Capacity improved, drawdown and tail IC still failed |
| 3 | `public_technical_tail_guard` | 2 | 0 | 0 | Capacity improved further, tail IC stayed negative |
| total | all public technical variants | 8 | 0 | 2 | no standalone public-technical alpha |

## Metric Summary

| factor | round | Sharpe | overlap-adjusted Sharpe | max drawdown | mean rank IC | tail mean IC | capacity-limited trades | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `rsi_reversal_14` | 1 | 0.349 | 0.263 | -76.55% | 0.0467 | -0.0430 | 1275 | rejected |
| `bollinger_reversal_20` | 1 | 0.219 | 0.198 | -75.62% | 0.0487 | -0.0395 | 1133 | rejected |
| `donchian_position_20` | 1 | 0.183 | 0.165 | -80.76% | -0.0034 | -0.0859 | 6763 | rejected |
| `macd_histogram_12_26_9` | 1 | 0.232 | 0.140 | -95.68% | -0.0385 | -0.0052 | 176 | rejected |
| `bollinger_reversal_liquid_20` | 2 | 0.393 | 0.211 | -83.70% | 0.0568 | -0.0394 | 10 | rejected |
| `rsi_reversal_liquid_14_20` | 2 | 0.348 | 0.210 | -85.01% | 0.0559 | -0.0326 | 12 | rejected |
| `bollinger_reversal_liquid_low_tail_20` | 3 | 0.408 | 0.214 | -79.45% | 0.0312 | -0.0174 | 5 | rejected |
| `rsi_reversal_liquid_low_tail_14_20` | 3 | 0.412 | 0.213 | -79.80% | 0.0317 | -0.0222 | 2 | rejected |

## Diagnosis

The public technical mean-reversion family is not random noise at the IC layer, but it is not a tradable standalone portfolio under the current construction.

Evidence:

- RSI/Bollinger variants repeatedly show positive rank IC.
- Every version has unacceptable max drawdown, roughly -75% to -96%.
- Tail IC remains negative even after liquidity and tail guards.
- Capacity gates improved mechanics but did not fix economic outcome.
- Overlap-adjusted Sharpe stays near 0.14-0.26, well below a deployable threshold.
- Extreme trade return flags remain present, so raw total returns are contaminated by data/tail events.

This matches public-project discipline from Alphalens/Pyfolio-style workflows: IC alone is not enough; quantile spread, tail behavior, turnover/capacity, drawdown, and out-of-sample gates decide whether a factor is worth more budget.

## Direction Adjustment

Stop:

- Do not expand standalone RSI/Bollinger/Donchian/MACD parameter grids.
- Do not spend heavy walk-forward budget on public technical mean-reversion unless it passes a fast gate first.
- Do not promote any candidate from rounds 1-3.

Keep:

- Keep `public_technical`, `public_technical_liquidity`, and `public_technical_tail_guard` as reusable component sources.
- Keep the fast long-cycle diagnostic configs as cheap pre-walk-forward gates.
- Keep the round reports as negative evidence to avoid repeating the same family.

Next 3-round cycle:

- Round 4: daily-basic value/quality/liquidity composite with public technical only as a risk gate, not primary alpha.
- Round 5: residualized composite factor against size/liquidity/momentum exposures.
- Round 6: audit the daily-basic/residualized cycle and only then decide whether to spend walk-forward budget.

Hard gate before future walk-forward:

- max drawdown must be better than -50%.
- tail IC must not be significantly negative.
- extreme trade return flag must be false or explained by an explicit data-quality exclusion.
- capacity-limited trades must be zero or economically immaterial.
- overlap-adjusted Sharpe must be materially above 0.5 before heavier validation.

## Artifacts

- Round 1: `docs/research/cn_stock_public_technical_round1_2026-06-21.md`
- Round 2: `docs/research/cn_stock_public_technical_liquidity_round2_2026-06-21.md`
- Round 3: `docs/research/cn_stock_public_technical_tail_guard_round3_2026-06-21.md`
- Fast configs:
  - `configs/experiment_grid_cn_stock_public_technical_fast_20260621.json`
  - `configs/experiment_grid_cn_stock_public_technical_liquidity_fast_20260621.json`
  - `configs/experiment_grid_cn_stock_public_technical_tail_guard_fast_20260621.json`
