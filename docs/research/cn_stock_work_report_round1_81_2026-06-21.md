# CN Stock Factor Mining Work Report Rounds 1-81 - 2026-06-21

## Executive Summary

This report summarizes the office-desktop factor-mining work through Round81.

Machine and branch:

- Machine: `office_desktop`.
- Task: `factor_validation`.
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`.

Current research scope:

- CN A-share stock cross-sectional alpha.
- Not CN ETF rotation for this branch's current mandate.
- Research-to-review only. No broker connection, no account reads, no order placement, and no live trading.

Headline result:

- Promotable profitable factors: 0.
- Paper-ready factors: 0.
- Manual/live usable factors: 0.
- Current active research lead: 1, `anti_supertrend_volume_confirmed_10_3_20` as a bottom-exclusion risk-filter lead only.
- Current next action: costed walk-forward bottom-exclusion test for the anti-SuperTrend lead.

This is a poor profitability result, but it is not zero work. The main useful outcome is a harder research pipeline that now kills false positives faster: long-cycle replay, IC-to-portfolio gap audit, industry-neutral IC, bottom-exclusion diagnostics, cost/capacity gates, overlap-adjusted statistics, beta diagnostics, walk-forward validation, and the 3-round/10-round governance cadence.

## Measured Scope

Measured from local config and documentation artifacts:

- Research docs under `docs/research`: 107 markdown files.
- Experiment-grid configs under `configs`: 37.
- Unique factor names appearing in experiment-grid configs: 69.
- Unique CN stock factor names in CN stock grids: 62.
- Unique CN ETF factor names in CN ETF grids: 24.
- Estimated config-level parameter combinations in experiment-grid configs: 628.

These are not all newly mined profitable factors. Many are baselines, replayed candidates, portfolio translations, or rejected research controls. The correct profitability count is still 0 promotable.

## Round81 Result

Round81 rotated from RSRS into a pre-registered public SuperTrend/ATR-style family.

The round tested three existing public trend-volume factors:

- `supertrend_volume_confirmed_10_3_20`
- `anti_supertrend_volume_confirmed_10_3_20`
- `supertrend_volume_capacity_strict_10_3_20`

Direct grid result:

| Factor | Total Return | Sharpe | Overlap Adj Sharpe | Max DD | RankIC | RankIC t | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `supertrend_volume_confirmed_10_3_20` | -65.67% | -0.4707 | -0.3203 | -80.81% | -0.0659 | -9.28 | rejected |
| `anti_supertrend_volume_confirmed_10_3_20` | -12.42% | -0.0269 | -0.0178 | -62.34% | 0.0659 | 9.28 | rejected |
| `supertrend_volume_capacity_strict_10_3_20` | 0.56% | 0.0416 | 0.0281 | -47.75% | -0.0160 | -1.53 | rejected |

Bright Round81 data:

- `anti_supertrend_volume_confirmed_10_3_20` neutral RankIC 0.0888, t=46.29.
- `anti_supertrend_volume_confirmed_10_3_20` bottom-exclusion overlay t=7.00.
- Anti-SuperTrend bottom-exclusion positive overlay rate 68.82%.
- Anti-SuperTrend bottom bucket compounded return -99.33%, versus kept compounded return -62.65%.

Round81 decision:

- No direct SuperTrend factor is promotable.
- Raw SuperTrend is wrong-way and should be hibernated as a direct buy signal.
- Anti-SuperTrend is a possible bottom-tail avoidance signal, not a buy-list factor.
- Round82 should run one frozen, costed walk-forward exclusion test. If it fails, the SuperTrend family should be hibernated.

## Work By Phase

### Rounds 1-3: public technical baseline

Outcome:

- 8 public technical candidates.
- Promotable factors: 0.
- Research leads: 2 weak IC leads only.

Bright data:

- `rsi_reversal_14`: Sharpe 0.349, overlap-adjusted Sharpe 0.263, mean RankIC 0.0467.
- `bollinger_reversal_20`: Sharpe 0.219, overlap-adjusted Sharpe 0.198, mean RankIC 0.0487.

Why rejected:

- Max drawdowns around -75% to -96%.
- Tail IC remained negative.
- Capacity limits and extreme trade flags were present.
- The family had signal at the IC layer but failed portfolio-level gates.

### Rounds 4-6: daily-basic start and data-quality repair

Outcome:

- 3 daily-basic value/liquidity/tail candidates.
- Promotable factors: 0.
- Major data-quality issue found and blocked.

Bright data:

- The system found mass adjusted-ratio jump contamination and replayed the same parameters after repair.
- `value_low_turnover_low_tail_20` changed from a false pre-repair total return of 91.71 to a post-repair total return of 2.36, with post-repair Sharpe 0.668 and overlap-adjusted Sharpe 0.345.

Why rejected:

- The huge pre-repair returns were data contamination, not alpha.
- After repair, relative return stayed deeply negative.
- The work was valuable because it prevented fake alpha from becoming a promotion claim.

### Rounds 7-9: public trend-volume and inverse trend-volume

Outcome:

- 6 new trend-volume factor names.
- 12 focused portfolio variants.
- Promotable factors: 0.

Bright data:

- Raw trend-volume continuation was strongly wrong-way:
  - `supertrend_volume_confirmed_10_3_20`: mean IC -0.0450, total return -78%, max DD -93.47%.
  - `smart_money_trend_20`: mean IC -0.0491, total return -72%, max DD -92.45%.
- Inversion improved sign:
  - `anti_obv_breakout_low_tail_20`: mean IC 0.0341, total return 50%, Sharpe 0.238, overlap-adjusted Sharpe 0.135.

Why rejected:

- Inverse signals were too weak after costs and benchmark comparison.
- The best focused anti-OBV row had overlap-adjusted Sharpe only 0.121.

### Rounds 11-16: daily-basic residuals and public formula factors

Outcome:

- 6 new factor names in Rounds 11-13.
- 2 more formula variants in Round14.
- Promotable factors: 0.
- The project identified IC-to-portfolio translation as the central bottleneck.

Bright data:

- `formula_pv_corr_reversal_20`: RankIC about 0.076, RankIC t-stat 10.88.
- `formula_volume_contraction_reversal_20`: RankIC about 0.080, RankIC t-stat 10.25.
- Round12: 12/12 strong RankIC cases had IC-to-portfolio gaps.
- Round14: 8/8 strong RankIC cases had IC-to-portfolio gaps.
- Round16: 12/12 completed broad-basket cases still had strong RankIC, but all failed long-only translation.

Why rejected:

- RankIC and long-short spread existed, but naive long-only TopN portfolios did not beat the benchmark.
- The signals looked more like loser-avoidance or relative ranking signals than direct buy-list alphas.

### Rounds 17-45: ETF alignment detour and public ETF indicator checks

Outcome:

- The project temporarily moved toward CN ETF rotation after the practical objective was discussed.
- Later, the user clarified that this office desktop should mine CN stock factors while the laptop optimizes framework and method.
- ETF work is kept as context, not the current branch mandate.

Bright data:

- Round18 full-sample ETF candidate: total return 35.53%, relative return 3.79%, Sharpe 0.5739, max DD -19.93%.
- Round19 walk-forward result: 0 accepted folds out of 42.
- Round41 range-contraction short-window rows had high-looking Sharpe, but Round42 long-cycle same-parameter replay reduced the best rows to Sharpe around 0.44-0.53 and rejected them.
- Round45 strict capacity replay showed OBV/SuperTrend ETF paper returns weakened or turned negative after capacity realism.

Why rejected or demoted:

- Full-sample ETF approval did not survive walk-forward.
- Short-window results did not survive long-cycle replay.
- ETF data coverage had important long-cycle gaps.

### Rounds 46-50: stock industry metadata and translation infrastructure

Outcome:

- Stock metadata foundation built for industry audits.
- 5,529 A-share `stock_basic` rows became available for industry diagnostics.
- Industry-neutral IC audit and industry-neutral portfolio selector were added.
- `min_total_return` gate was added so losing strategies cannot pass just because they beat a worse benchmark.

Bright data:

- Round48 found 3 public formula factors that kept strong within-industry RankIC.
- Round49 rejected 12/12 industry-neutral portfolio cases, preventing IC-only promotion.
- Round50 packaged code/config/test/doc work and excluded generated data from sync.

### Rounds 55-57: smart-money, anti-OBV, and composite risk-filter bridge

Outcome:

- 9 candidates or risk filters evaluated.
- Promotable profitable factors: 0.
- Paper-ready factors: 0.

Bright data:

- `smart_money_reversal_value_20`: direct Sharpe 0.3196; bottom-exclusion overlay t=4.12.
- `anti_obv_breakout_low_tail_20`: bottom-exclusion overlay t=8.07.
- `risk_filter_bridge_agreement_20`: bottom-exclusion overlay t=8.46, positive rate 70.34%.
- Best costed bottom-exclusion portfolios had positive relative return, for example 46.57% total and 33.83% relative in one anti-OBV view.

Why rejected:

- Portfolio Sharpe stayed below 0.20.
- Max drawdowns remained around -59% to -62%.
- Bottom-tail detection was real, but absolute portfolio quality was poor.

### Rounds 58-63: public price-volume formula replay and costed exclusion

Outcome:

- 8 public formula price-volume factors replayed with industry-neutral IC.
- Promotable factor: 0.
- One reserve research lead: `formula_pv_corr_reversal_20` as an exclusion/risk-control candidate.

Bright data:

- Round58 industry-neutral IC gate:
  - 8/8 factors classified as industry-neutral signals.
  - `formula_volume_contraction_reversal_20`: neutral RankIC 0.0910, neutral t=49.41.
  - `formula_pv_corr_reversal_20`: neutral RankIC 0.0879, neutral t=49.86.
- Round58 best portfolio:
  - `formula_pv_corr_reversal_20` industry-neutral top100 rebalance 5.
  - Total return 35.48%.
  - Sharpe 0.3134.
  - Overlap-adjusted Sharpe 0.1771.
  - Max DD -26.71%.
  - Capacity-limited trades 0.
- Round60 bottom-exclusion overlay:
  - rebalance 5 overlay t=8.19, positive rate 68.43%.
  - rebalance 10 overlay t=6.42, positive rate 70.45%.
- Round61 costed bottom-exclusion portfolio:
  - best rebalance 5 total return 111.83%;
  - best rebalance 5 relative return 46.85%;
  - capacity-limited trades 0.

Why rejected:

- Round61 overlap-adjusted Sharpe was only 0.1604.
- Round61 max drawdown was -56.52%.
- Exposure sensitivity reduced drawdown but did not lift overlap-adjusted Sharpe.
- The line was hibernated as a standalone profitable factor.

### Rounds 64-69: daily-basic residual composites and bridge tests

Outcome:

- Daily-basic residual rotation found strong neutral IC, then failed portfolio conversion.
- Industry-breadth bridge tool was added.
- Promotable profitable factors: 0.

Bright data:

- Round64 best neutral RankIC values: 0.0556, 0.0546, and 0.0425.
- Round65 best total return: 30.84%, best overlap-adjusted Sharpe 0.1733, capacity not the blocker.
- Round66 produced two bottom-exclusion leads:
  - `resid_value_low_turnover_quality_20`
  - `resid_value_reversal_low_tail_20`
- Round69 industry-breadth bridge produced positive industry RankIC, but positive excess rate only 52%-53%.

Why rejected:

- Top100 long-only relative return failed.
- Costed bottom-exclusion Sharpe stayed around 0.08-0.09.
- Max drawdown stayed around -64%.

### Rounds 71-80: risk-filter bridge, beta diagnostics, RSRS, and safe sync

Outcome:

- Public risk-filter bridge was tested through cash overlays, beta exposure, hedged spread, and stress.
- RSRS was pre-registered, tested, translated, walk-forwarded, rejected, and hibernated.
- Round80 safely pushed the lightweight sync package.

Bright data:

- Round71 best static cash overlay:
  - total return 18.89%;
  - relative return 19.62%;
  - positive relative folds 10/11;
  - overlap-adjusted Sharpe 0.0686.
- Round72 best dynamic cash overlay:
  - total return 11.39%;
  - relative return 13.17%;
  - max DD improved to -26.09%;
  - overlap-adjusted Sharpe 0.0586.
- Round73 beta diagnostic:
  - residual alpha t-stat 4.39-5.42;
  - residual Sharpe 0.62-0.76;
  - but R2 0.992-0.994, showing benchmark beta dominance.
- Round74 found and fixed a short-leg cost-sign bug:
  - corrected best spread total return -12.91%;
  - corrected overlap-adjusted Sharpe -0.516.
- Round77 RSRS direct grid:
  - `rsrs_reversal_18_60` top100 total return 72.07%;
  - Sharpe 0.272;
  - overlap-adjusted Sharpe 0.191;
  - RankIC 0.0214, RankIC t=4.77.
- Round78 RSRS translation:
  - industry-neutral RankIC 0.0253, t=24.00;
  - bottom-exclusion overlay t=5.39;
  - positive overlay rate 66.28%.
- Round79 RSRS costed walk-forward:
  - 7 rolling test folds;
  - accepted folds 0/7;
  - mean test total return 2.86%;
  - mean test relative return 0.46%;
  - mean test overlap-adjusted Sharpe 0.0766;
  - worst test DD -17.90%;
  - capacity-limited trades 0.
- Round80 sync:
  - GitHub push completed after validation;
  - commit `c54fe106d56bf0745ad9ae09077e3ab3980dc95c`;
  - generated data stayed out of Git.

Why rejected:

- Cash overlays reduced exposure but did not create enough alpha.
- Beta diagnostics showed benchmark dependence.
- Corrected hedged spreads were negative.
- RSRS had real ranking evidence, but zero accepted costed walk-forward folds.

## Main Pattern Found

The project has repeatedly found signals that rank stocks better than random, especially in bottom-tail detection.

The project has not found a stock long-only factor that converts that ranking signal into robust, costed, capacity-aware, benchmark-competitive portfolio returns.

Repeated pattern:

- IC or neutral IC is often strong.
- Bottom bucket is often bad.
- Direct top bucket is not good enough.
- Broad retained portfolios still carry too much beta and drawdown.
- Costs, capacity, drawdown, and overlap-adjusted statistics erase the apparent edge.
- Walk-forward validation kills short-sample or full-sample positives.

## Most Important Bright Data

These are the numbers most worth remembering, because they explain where the real signal may be:

| Source | Bright Evidence | Why It Matters | Why Not Promoted |
|---|---|---|---|
| Round58 `formula_pv_corr_reversal_20` | neutral RankIC 0.0879, t=49.86 | strong within-industry ranking signal | portfolio Sharpe only 0.3134, overlap Sharpe 0.1771 |
| Round58 `formula_volume_contraction_reversal_20` | neutral RankIC 0.0910, t=49.41 | strongest public formula neutral IC | capacity/drawdown/portfolio conversion failed |
| Round60 `formula_pv_corr_reversal_20` overlay | t=8.19, positive rate 68.43% | strong bottom-tail avoidance | costed portfolio drawdown -56.52% |
| Round55-57 risk filters | overlay t up to 8.46, positive rate 70.34% | bottom exclusion is repeatable | costed portfolio Sharpe below 0.20 |
| Round64 daily-basic residuals | neutral RankIC 0.0556, 0.0546, 0.0425 | Tushare daily-basic data does contain cross-sectional information | long-only conversion failed relative return |
| Round78 RSRS reversal | neutral RankIC 0.0253, t=24.00; overlay t=5.39 | public RSRS signal had real information | Round79 accepted folds 0/7 |
| Round81 anti-SuperTrend | neutral RankIC 0.0888, t=46.29; overlay t=7.00 | newest bottom-exclusion lead | direct portfolio lost money; WF not yet passed |
| Round74 engineering | cost-sign bug fixed; corrected spread Sharpe -0.516 | blocked a false positive | no alpha after correction |
| Round4-6 data repair | adjusted-ratio artifact blocked and replayed | blocked fake historical profits | post-repair economics still weak |

## Engineering And Process Output

Reusable capabilities added or strengthened:

- CN stock startup gate.
- 3-round review cadence.
- 10-round GitHub sync cadence.
- Safe sync script usage with forbidden data and secret path checks.
- Data manifest and adjusted-ratio anomaly handling.
- Clean CN stock authority-bars config.
- `min_total_return` decision gate.
- IC-to-portfolio gap audit.
- Industry-neutral IC audit.
- Industry-neutral portfolio selector.
- Bottom-exclusion overlay audit.
- Bottom-exclusion walk-forward validator.
- Dynamic cash overlay backtest.
- Benchmark beta exposure audit.
- Beta-hedged spread audit.
- Public RSRS factors.
- Public SuperTrend pre-registration and signal-direction audit flow.
- Tests covering the reusable tools and startup-gate requirements.

Round80 GitHub sync evidence:

- Commit pushed: `c54fe106d56bf0745ad9ae09077e3ab3980dc95c`.
- Sync package included code, configs, tests, and lightweight docs.
- `data/raw`, `data/processed`, `data/reports`, logs, tokens, credentials, broker/account/order data were excluded.

## Why There Is Still No Useful Profit Factor

The main reason is not that every formula is pure noise. The repeated evidence says the formulas often identify relative rank or bottom-tail risk. The failure is monetization:

1. Long-only TopN is the wrong translation for many of these signals.

The edge is often "avoid the worst names" rather than "buy the best names."

2. Benchmark and market beta dominate.

Several positive-looking return streams were mostly benchmark exposure or cash/exposure effects, not standalone alpha.

3. Risk-adjusted return is weak.

Many cases show positive total or relative return, but overlap-adjusted Sharpe stays far below promotion thresholds.

4. Drawdown is too large.

Bottom-exclusion portfolios often still draw down 50%-65%, which is not acceptable for a deployable factor.

5. Public indicators have thin edges.

SuperTrend, OBV, RSRS, RSI/Bollinger, and formulaic price-volume signals can contain information, but costs, capacity, and fold instability remove most of it.

6. The stricter process is now rejecting false positives.

This is painful but necessary. Earlier workflows could have mistaken short-window, data-contaminated, or beta-dominated results for alpha.

## Current Direction

Do not continue broad SuperTrend parameter expansion.

Do not promote raw SuperTrend, RSRS, daily-basic residual, public price-volume, or risk-filter bridge results.

Continue only this narrow Round82 path:

`round82_public_supertrend_bottom_exclusion_costed_walk_forward`

Round82 must:

- use only `anti_supertrend_volume_confirmed_10_3_20`;
- keep parameters frozen;
- test bottom 20% exclusion;
- use rolling train/test walk-forward;
- include 10 bps cost, 20 bps impact, 1% ADV capacity, and strict date separation;
- require overlap-adjusted Sharpe, drawdown, fold stability, and capacity gates;
- hibernate the SuperTrend family if the walk-forward gate fails.

If Round82 fails, the next family should rotate rather than tune:

- stock-to-industry or stock-to-ETF breadth bridge if mapping is reliable;
- stronger Tushare fundamental/quality/earnings-style data if available;
- portfolio construction research that targets lower drawdown and beta control before new factor-name mining.
