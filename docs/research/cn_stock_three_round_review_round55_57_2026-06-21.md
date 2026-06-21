# CN Stock Three-Round Review - Rounds 55-57 - 2026-06-21

## Scope

This review covers the three-round governance checkpoint required after Rounds 55, 56, and 57.

Rounds reviewed:

- Round55: `daily_basic_smart_money_quality`
- Round56: public trend-volume anti risk filters
- Round57: composite public plus daily-basic risk-filter bridge

The review uses the long-cycle CN stock authority data from 2015-01-05 through 2025-12-31 with execution lag, costs, market impact, capacity checks, overlap-aware statistics, and yearly fold checks.

## Count

Unique candidates evaluated in this three-round block:

- Round55: 3 smart-money-quality factors
- Round56: 3 public trend-volume anti factors
- Round57: 3 composite bridge factors

Total evaluated in this block: 9 candidate factors or risk filters.

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads only:

- `smart_money_reversal_value_20`
- `anti_obv_breakout_low_tail_20`
- `risk_filter_bridge_anti_obv_weighted_20`
- `risk_filter_bridge_agreement_20`

Secondary research leads:

- `smart_money_quality_lowvol_20`
- `risk_filter_bridge_equal_20`

## Main Finding

The project found a repeatable shape, but not a profitable engine:

- top-tail buying is weak;
- bottom-tail exclusion is statistically strong;
- costed broad-basket risk filtering improves relative return;
- absolute portfolio quality remains poor.

The common failure is not "no signal". The common failure is IC-to-portfolio conversion.

## Evidence Summary

| Round | Best Direct Result | Best Overlay Result | Best Costed Portfolio Result | Decision |
|---|---|---|---|---|
| 55 | `smart_money_reversal_value_20`: Sharpe 0.3196, rejected by relative return | reb5 t=4.12, positive rate 58.98%, bottom compound -96.89% | total 53.66%, relative +26.97%, Sharpe 0.1782, max DD -61.27% | research lead only |
| 56 | Raw public trend-volume continuation already rejected earlier | `anti_obv_breakout_low_tail_20`: reb5 t=8.07, bottom compound -98.73% | total 46.57%, relative +33.83%, Sharpe 0.1834, max DD -59.20% | research lead only |
| 57 | `risk_filter_bridge_agreement_20`: Sharpe 0.2200, rejected by relative return | agreement reb5 t=8.46, positive rate 70.34%, bottom compound -99.56% | anti-obv weighted reb10 total 23.44%, relative +32.30%, Sharpe 0.0920, max DD -61.93% | research lead only |

## Why The Work Is Still Poor

1. The factors identify bad stocks better than good stocks.

IC and quantile spread are real, but most of the spread comes from the bottom bucket being terrible. Buying the top bucket directly does not create enough absolute return after costs.

2. Relative improvement hides weak absolute performance.

The bottom-exclusion portfolios often beat a weak or negative benchmark, but Sharpe remains below 0.20 and drawdown remains around -60%. That cannot be treated as an investable result.

3. The portfolio construction layer is too blunt.

Broad bottom 20% exclusion leaves a large, beta-heavy basket. It removes some bad names but does not construct a high-quality portfolio.

4. Industry and size exposures are not yet decomposed.

The current evidence might be excluding small, illiquid, distressed, or sector-specific junk rather than capturing a robust alpha. Without industry/size neutral IC, the signal story is incomplete.

5. The audit pipeline wastes computation.

Round57 recomputed the same 25,249,353-row factor matrix for the direct grid, reb5 overlay, reb10 overlay, reb5 portfolio, and reb10 portfolio. This is avoidable and slows continuous mining.

6. Multiple testing pressure is rising.

The last three rounds tested nine candidates plus several portfolio views. No promotion claim should be made without cumulative multiple-testing accounting and stricter out-of-sample gates.

## Direction Decision

Stop doing more parameter expansion inside smart-money quality, public trend-volume anti filters, or their simple composite bridge.

The next block should rotate to a different, explainable public alpha family and improve the research infrastructure at the same time.

Next direction:

`industry_neutral_public_formula_price_volume_cached_replay_batch`

Required changes before the next mining run:

- reuse one precomputed factor matrix, labels, and filtered bars across direct grid, overlay, and portfolio audits;
- add industry/size-neutral IC audit before treating a stock factor as real alpha;
- keep bottom-exclusion as a diagnostic layer, not promotion evidence by itself;
- require absolute risk gates, not just relative return;
- record all tested candidates in the cumulative multiple-testing ledger.

## Round 58 Starting Hypothesis

Use public, explainable price-volume formula factors as the next family:

- price-volume divergence,
- skip momentum,
- short-term reversal,
- low volatility/downside volatility,
- liquidity and volume shock filters,
- simple formula-style combinations inspired by public alpha libraries.

The test order should be:

1. Full-sample same-parameter factor matrix.
2. IC, rank IC, quantile spread, turnover, and decay.
3. Industry-neutral and size-neutral IC.
4. Direct costed portfolio only if the neutral IC survives.
5. Bottom-exclusion overlay only if direct top-tail fails but bottom-tail is statistically bad.
6. Costed risk-filter portfolio with absolute Sharpe, drawdown, and yearly-fold gates.

## Guardrail Update

Do not promote any result that only clears bottom-exclusion overlay.

For research lead status, require at least one of:

- significant neutral IC after industry/size controls;
- costed portfolio relative folds >= 8/11 with overlap-adjusted Sharpe above 0.20 and max drawdown better than -40%;
- clear drawdown reduction against a comparable benchmark, not only relative return.

For promotion status, require:

- costed walk-forward evidence,
- capacity controls,
- overlap-adjusted Sharpe above the configured promotion gate,
- max drawdown within gate,
- cumulative multiple-testing review,
- no 2026 holdout tuning.
